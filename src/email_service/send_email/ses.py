import logging
import random
import time
from email.mime.application import MIMEApplication
from pathlib import Path

import boto3
import time_util
from botocore.exceptions import ClientError
from certificate_generator import generate_certificate
from email_util import attach_files_to_message, create_email_message
from template_util import replace_placeholders

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ses_client = boto3.client("ses", region_name="ap-northeast-1")

def send_email_with_backoff_delay(delay_factor=1):
    """Simple delay logic for controlled sending."""
    base_delay = random.uniform(0.5, 1.5) 
    delay = delay_factor * base_delay
    logger.info("Delaying for %.2f seconds to avoid throttling.", delay)
    time.sleep(delay)

def send_email(
    subject: str,
    template_content: str,
    row: dict[str, any],
    display_name: str,
    reply_to: str,
    sender_local_part: str,
    attachment_file_ids: list[str] = None,
    is_generate_certificate: bool = False,
    run_id: str = None,
    cc: list[str] = None,
    bcc: list[str] = None,
) -> tuple:
    try:
        logger.info("Row data before formatting: %s", row)
        template_content = template_content.replace("\r", "")

        recipient_email = row.get("Email")
        if not recipient_email:
            logger.warning("Email address not found in row: %s", row)
            return None, "FAILED"

        formatted_row = {k: str(v) for k, v in row.items()}
        logger.info("Formatted row: %s", formatted_row)
        formatted_content = replace_placeholders(template_content, formatted_row)

        msg = create_email_message(
            subject,
            formatted_content,
            recipient_email,
            display_name,
            reply_to,
            cc,
            bcc,
            sender_local_part,
        )

        attach_files_to_message(msg, attachment_file_ids)
        logger.info("Will generate certificate: %s", str(is_generate_certificate))
        certificate_path = None

        if is_generate_certificate:
            participant_name = row.get("Name")
            certificate_text = row.get("Certificate Text")
            certificate_path = generate_certificate(
                run_id, participant_name, certificate_text
            )

            with open(certificate_path, "rb") as cert_file:
                attachment = MIMEApplication(cert_file.read())
                attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=f"{participant_name}_certificate.pdf",
                )
                msg.attach(attachment)
                logger.info("Attached certificate for: %s", participant_name)

        # Implement a simple backoff delay logic to avoid throttling
        send_email_with_backoff_delay()

        try:
            # Send the email using the AWS SES client
            response = ses_client.send_raw_email(
                Source=msg["From"],
                Destinations=[recipient_email] + (cc or []) + (bcc or []),
                RawMessage={"Data": msg.as_string()},
            )
            logger.info("Email sent. Message ID: %s", response["MessageId"])

            sent_time = time_util.get_current_utc_time()
            logger.info(
                "Email sent to %s at %s",
                row.get("Email", "Unknown"),
                sent_time,
            )

            # Delete the certificate file after successful email sending
            if certificate_path:
                Path(certificate_path).unlink()

            return sent_time, "SUCCESS"
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logger.error("Failed to send email: %s - %s", error_code, error_message)
        except Exception as e:
            logger.error("Failed to send email to %s: %s", recipient_email, e)
    except Exception as e:
        logger.error("Failed to process email for %s: %s", recipient_email, e)

    if certificate_path:
        try:
            Path(certificate_path).unlink()
        except Exception as e:
            logger.error("Failed to delete certificate file: %s", e)

    return None, "FAILED"
