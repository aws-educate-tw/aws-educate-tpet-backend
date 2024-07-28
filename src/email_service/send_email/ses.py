import logging
import os
import re
import uuid
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

import boto3
import requests
import time_util
from botocore.exceptions import ClientError
from certificate_generator import generate_certificate
from current_user_util import current_user_util  # Import the global instance
from dynamodb import save_to_dynamodb
from s3 import read_html_template_file_from_s3

from file_service import FileService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ses_client = boto3.client("ses", region_name="ap-northeast-1")

SENDER_EMAIL = "cloudambassador@aws-educate.tw"
REPLY_TO_EMAIL = "awseducate.cloudambassador@gmail.com"
CHARSET = "utf-8"
BUCKET_NAME = os.getenv("BUCKET_NAME")
PRIVATE_BUCKET_NAME = os.getenv("PRIVATE_BUCKET_NAME")
CERTIFICATE_TEMPLATE_FILE_S3_OBJECT_KEY = (
    "templates/[template] AWS Educate certificate.pdf"
)

# Initialize FileService
file_service = FileService()


def download_file_content(file_url):
    """
    Download the content of the file from the given URL.

    :param file_url: URL of the file to be downloaded.
    :return: Content of the downloaded file.
    """
    response = requests.get(file_url, timeout=25)
    response.raise_for_status()
    return response.content


def create_email_message(
    subject, formatted_content, recipient_email, display_name, reply_to
):
    """
    Create an email message with the given title, content, recipient, and display name.

    :param email_title: Title of the email.
    :param formatted_content: Content of the email in HTML format.
    :param recipient_email: Email address of the recipient.
    :param display_name: Display name of the sender.
    :return: A MIMEMultipart email message.
    """

    # Create a multipart/mixed parent container.
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = formataddr((display_name, SENDER_EMAIL))
    msg["To"] = recipient_email
    msg["Reply-To"] = reply_to

    # Create a multipart/alternative child container.
    msg_body = MIMEMultipart("alternative")
    msg.attach(msg_body)

    # Encode the text and HTML content and set the character encoding.
    textpart = MIMEText(formatted_content, "plain", CHARSET)
    htmlpart = MIMEText(formatted_content, "html", CHARSET)

    # Add the text and HTML parts to the child container.
    msg_body.attach(textpart)
    msg_body.attach(htmlpart)

    return msg


def attach_files_to_message(msg, file_ids):
    """
    Attach files to the email message.

    :param msg: The email message to attach files to.
    :param file_ids: List of file IDs to be attached.
    """
    if not file_ids:
        return

    logger.info("Processing file attachments.")
    for file_id in file_ids:
        try:
            file_info = file_service.get_file_info(
                file_id, current_user_util.get_current_user_access_token()
            )
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
                logger.warning("File info incomplete for file_id: %s", file_id)
        except Exception as e:
            logger.error("Error processing file attachment %s: %s", file_id, e)
            # Continue to the next file rather than failing the entire email


def replace_placeholders(template, values):
    """
    Replace placeholders in the template with actual values.

    :param template: The template string with placeholders.
    :param values: A dictionary of values to replace the placeholders.
    :return: The template string with placeholders replaced by actual values.
    """

    def replacement(match):
        variable_name = match.group(1)
        return values.get(variable_name, match.group(0))

    # Using Regular Expressions to Match and Replace {{variable}}
    pattern = r"\{\{(.*?)\}\}"
    return re.sub(pattern, replacement, template)


def send_email(
    subject: str,
    template_content: str,
    row: dict[str, any],
    display_name: str,
    reply_to: str,
    attachment_file_ids: list[str] = None,
    is_generate_certificate: bool = False,
    run_id: str = None,
) -> tuple:
    """
    Send an email to the recipient with the provided details.

    :param subject: The subject of the email.
    :param template_content: The content template of the email with placeholders.
    :param row: A dictionary containing recipient and email details.
    :param display_name: The display name of the sender.
    :param attachment_file_ids: A list of file IDs for attachments (optional).
    :param is_generate_certificate: A boolean flag to indicate if a certificate should be generated (optional).
    :param run_id: The run ID for tracking the operation (optional).
    :return: A tuple containing the sent time (or None) and the status ("SUCCESS" or "FAILED").
    """
    try:
        logger.info("Row data before formatting: %s", row)
        template_content = template_content.replace("\r", "")

        recipient_email = row.get("Email")
        if not recipient_email:
            logger.warning("Email address not found in row: %s", row)
            return None, "FAILED"

        # Convert all values in the row to strings for consistent formatting
        formatted_row = {k: str(v) for k, v in row.items()}
        logger.info("Formatted row: %s", formatted_row)

        # Replace placeholders in the template content with actual data
        formatted_content = replace_placeholders(template_content, formatted_row)

        # Create the email message object
        msg = create_email_message(
            subject, formatted_content, recipient_email, display_name, reply_to
        )

        # Attach any specified files to the email
        attach_files_to_message(msg, attachment_file_ids)
        logger.info("Will generate certificate: %s", str(is_generate_certificate))
        certificate_path = None

        # Generate a certificate if required and attach it to the email
        if is_generate_certificate:
            participant_name = row.get("Name")
            certificate_text = row.get("Certificate Text")
            certificate_path = generate_certificate(
                run_id, participant_name, certificate_text
            )

            # Attach the generated certificate to the email
            with open(certificate_path, "rb") as cert_file:
                attachment = MIMEApplication(cert_file.read())
                attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=f"{participant_name}_certificate.pdf",
                )
                msg.attach(attachment)
                logger.info("Attached certificate for: %s", participant_name)

        try:
            # Send the email using the AWS SES client
            response = ses_client.send_raw_email(
                Source=msg["From"],
                Destinations=[recipient_email],
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

    # Delete the certificate file if sending the email failed
    if certificate_path:
        try:
            Path(certificate_path).unlink()
        except Exception as e:
            logger.error("Failed to delete certificate file: %s", e)

    return None, "FAILED"


def process_email(
    email_data: dict,
    row: list[dict[str, any]],
) -> tuple:
    """
    Process email sending for a given row of data.

    :param email_data: Dictionary containing email metadata such as subject, display_name, template_file_id, etc.
    :param row: A dictionary representing a single row of data from Excel, containing email recipient and placeholder values.
    :return: Status and email ID of the email sending operation.
    """
    recipient_email = row.get("Email")
    email_id = str(uuid.uuid4().hex)

    logger.info("Row data: %s", row)
    if not re.match(r"[^@]+@[^@]+\.[^@]+", recipient_email):
        logger.warning("Invalid email address provided: %s", recipient_email)
        return "FAILED", email_id
    # Get template file information and content
    template_file_info = file_service.get_file_info(
        email_data.get("template_file_id"),
        current_user_util.get_current_user_access_token(),
    )
    template_file_s3_object_key = template_file_info["s3_object_key"]
    template_content = read_html_template_file_from_s3(
        bucket=BUCKET_NAME, template_file_s3_key=template_file_s3_object_key
    )

    # Send email
    sent_time, status = send_email(
        email_data.get("subject"),
        template_content,
        row,
        email_data.get("display_name"),
        REPLY_TO_EMAIL,
        email_data.get("attachment_file_ids"),
        email_data.get("is_generate_certificate"),
        email_data.get("run_id"),
    )
    updated_at = time_util.get_current_utc_time()

    # Create the item dictionary
    item = {
        "run_id": email_data.get("run_id"),
        "email_id": email_id,
        "display_name": email_data.get("display_name"),
        "status": status,
        "recipient_email": recipient_email,
        "template_file_id": email_data.get("template_file_id"),
        "spreadsheet_file_id": email_data.get("spreadsheet_file_id"),
        "created_at": email_data.get("created_at"),
        "row_data": row,
        "sent_at": sent_time,
        "updated_at": updated_at,
        "is_generate_certificate": email_data.get("is_generate_certificate"),
    }

    # Save to DynamoDB
    save_to_dynamodb(item)
    return status, email_id
