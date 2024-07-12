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
CHARSET = "utf-8"


def download_file_content(file_url):
    """
    Download the content of the file from the given URL.

    :param file_url: URL of the file to be downloaded.
    :return: Content of the downloaded file.
    """
    response = requests.get(file_url, timeout=25)
    response.raise_for_status()
    return response.content


def create_email_message(email_title, formatted_content, recipient_email, display_name):
    """
    Create an email message with the given title, content, recipient, and display name.

    :param email_title: Title of the email.
    :param formatted_content: Content of the email in HTML format.
    :param recipient_email: Email address of the recipient.
    :param display_name: Display name of the sender.
    :return: A MIMEMultipart email message.
    """
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
    ses_client, email_title, template_content, row, display_name, file_ids=None
):
    """
    Send an email using AWS SES.

    :param ses_client: Boto3 SES client.
    :param email_title: Title of the email.
    :param template_content: Content of the email template.
    :param row: A dictionary representing a single row of data from Excel, containing email recipient and placeholder values.
    :param display_name: Display name of the sender.
    :param file_ids: List of file IDs to be attached.
    :return: Sent time and status of the email sending operation.
    """
    try:
        logger.info("Row data before formatting: %s", row)
        logger.info("Template content before replacements: %s", template_content)
        template_content = template_content.replace("\r", "")
        logger.info("Template content after replacements: %s", template_content)

        recipient_email = row.get("Email")
        if not recipient_email:
            logger.warning("Email address not found in row: %s", row)
            return None, "FAILED"

        formatted_row = {k: str(v) for k, v in row.items()}
        logger.info("Formatted row: %s", formatted_row)

        formatted_content = replace_placeholders(template_content, formatted_row)
        logger.info("Formatted content: %s", formatted_content)

        msg = create_email_message(
            email_title, formatted_content, recipient_email, display_name
        )

        attach_files_to_message(msg, file_ids)

        # Send the email using SES
        try:
            response = ses_client.send_raw_email(
                Source=msg["From"],
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


def process_email(
    ses_client,
    email_title,
    template_content,
    recipient_email,
    row,
    display_name,
    run_id,
    template_file_id,
    spreadsheet_id,
    created_at,
    email_id,
    file_ids=None,
):
    """
    Process email sending for a given row of data.

    :param ses_client: Boto3 SES client.
    :param email_title: Title of the email.
    :param template_content: Content of the email template.
    :param recipient_email: Email address of the recipient.
    :param row: A dictionary representing a single row of data from Excel, containing email recipient and placeholder values.
    :param display_name: Display name of the sender.
    :param run_id: Run ID for tracking the email sending operation.
    :param template_file_id: File ID of the email template.
    :param spreadsheet_id: File ID of the spreadsheet.
    :param created_at: Timestamp of when the email was created.
    :param email_id: Unique email ID.
    :param file_ids: List of file IDs to be attached.
    :return: Status and email ID of the email sending operation.
    """
    logger.info("Row data: %s", row)
    if not re.match(r"[^@]+@[^@]+\.[^@]+", recipient_email):
        logger.warning("Invalid email address provided: %s", recipient_email)
        return "FAILED", email_id

    sent_time, status = send_email(
        ses_client, email_title, template_content, row, display_name, file_ids
    )
    updated_at = time_util.get_current_utc_time()
    save_to_dynamodb(
        run_id=run_id,
        email_id=email_id,
        display_name=display_name,
        status=status,
        recipient_email=recipient_email,
        template_file_id=template_file_id,
        spreadsheet_file_id=spreadsheet_id,
        created_at=created_at,
        row_data=row,
        sent_at=sent_time,
        updated_at=updated_at,
    )
    return status, email_id
