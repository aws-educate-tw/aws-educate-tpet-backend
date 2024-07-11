import logging
import re
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
import time_util
from botocore.exceptions import ClientError
from dynamodb import save_to_dynamodb

from file_service import get_file_info

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SENDER_EMAIL = "awseducate.cloudambassador@gmail.com"


def download_file_content(file_url):
    response = requests.get(file_url, timeout=25)
    response.raise_for_status()
    return response.content


def send_email(
    ses_client, email_title, template_content, row, display_name, file_ids=None
):
    try:
        template_content = template_content.replace("\r", "")
        template_content = re.sub(r"\{\{(.*?)\}\}", r"{\1}", template_content)
        recipient_email = row.get("Email")
        if not recipient_email:
            logger.warning("Email address not found in row: %s", row)
            return None, "FAILED"
        try:
            formatted_row = {k: str(v) for k, v in row.items()}
            formatted_content = template_content.format(**formatted_row)
            formatted_source_email = f"{display_name} <{SENDER_EMAIL}>"

            # Create a multipart/mixed parent container.
            msg = MIMEMultipart("mixed")
            msg["Subject"] = email_title
            msg["From"] = formatted_source_email
            msg["To"] = recipient_email

            # Create a multipart/alternative child container.
            msg_body = MIMEMultipart("alternative")
            msg.attach(msg_body)

            # Encode the text and HTML content and set the character encoding.
            textpart = MIMEText(formatted_content, "plain", "utf-8")
            htmlpart = MIMEText(formatted_content, "html", "utf-8")

            # Add the text and HTML parts to the child container.
            msg_body.attach(textpart)
            msg_body.attach(htmlpart)

            # If there are file IDs, process each file and add it as an attachment.
            if file_ids:
                logger.info("Processing file attachments.")
                for file_id in file_ids:
                    try:
                        file_info = get_file_info(file_id)
                        file_url = file_info.get("file_url")
                        file_name = file_info.get("file_name")
                        file_size = file_info.get("file_size")

                        logger.info("Processing file: %s", file_name)

                        if file_url and file_name:
                            # Download the file and attach it
                            file_content = download_file_content(file_url)
                            attachment = MIMEApplication(file_content)
                            attachment.add_header(
                                "Content-Disposition", "attachment", filename=file_name
                            )
                            if file_size:
                                attachment.add_header("Content-Length", str(file_size))
                            msg.attach(attachment)
                            logger.info("Attached file: %s", file_name)
                        else:
                            logger.warning(
                                "File info incomplete for file_id: %s", file_id
                            )
                    except Exception as e:
                        logger.error(
                            "Error processing file attachment %s: %s", file_id, e
                        )
                        # Continue to the next file rather than failing the entire email

            # Send the email using SES
            try:
                response = ses_client.send_raw_email(
                    Source=formatted_source_email,
                    Destinations=[recipient_email],
                    RawMessage={"Data": msg.as_string()},
                )
                logger.info("Email sent. Message ID: %s", response["MessageId"])
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                error_message = e.response["Error"]["Message"]
                logger.error("Failed to send email: %s - %s", error_code, error_message)
                return None, "FAILED"

            sent_time = time_util.get_current_utc_time()
            logger.info(
                "Email sent to %s at %s",
                row.get("Email", "Unknown"),
                sent_time,
            )
            return sent_time, "SUCCESS"
        except Exception as e:
            logger.error("Failed to send email to %s: %s", recipient_email, e)
            return None, "FAILED"
    except Exception as e:
        logger.error("Error in send_email: %s", e)
        return None, "FAILED"


def process_email(
    ses_client,
    email_title,
    template_content,
    row,
    display_name,
    run_id,
    template_file_id,
    spreadsheet_id,
    email_id,
    file_ids=None,
):
    recipient_email = str(row.get("Email", ""))
    if not re.match(r"[^@]+@[^@]+\.[^@]+", recipient_email):
        logger.warning("Invalid email address provided: %s", recipient_email)
        return "FAILED", email_id

    sent_time, status = send_email(
        ses_client, email_title, template_content, row, display_name, file_ids
    )
    updated_at = time_util.get_current_utc_time()
    save_to_dynamodb(
        run_id,
        email_id,
        display_name,
        status,
        recipient_email,
        template_file_id,
        spreadsheet_id,
        time_util.get_current_utc_time(),
        sent_at=sent_time,
        updated_at=updated_at,
    )
    return status, email_id
