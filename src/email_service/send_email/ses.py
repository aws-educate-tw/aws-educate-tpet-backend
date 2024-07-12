import logging
import os
import re
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Tuple

import fitz  # PyMuPDF
import requests
import time_util
from botocore.exceptions import ClientError
from dynamodb import save_to_dynamodb
from s3 import read_file_from_s3, upload_file_to_s3

from file_service import get_file_info

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SENDER_EMAIL = "awseducate.cloudambassador@gmail.com"
CHARSET = "utf-8"
BUCKET_NAME = os.getenv("BUCKET_NAME")
PRIVATE_BUCKET_NAME = os.getenv("PRIVATE_BUCKET_NAME")
CERTIFICATE_TEMPLATE_FILE_S3_OBJECT_KEY = (
    "templates/[template] AWS Educate certificate.pdf"
)
# Constants for certificate generation
FONT_SIZE_NAME = 32
FONT_SIZE_EVENT = 18
COORD_NAME = (365, 210)
COORD_EVENT = (250, 265)


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

    # Create a multipart/mixed parent container.
    msg = MIMEMultipart("mixed")
    msg["Subject"] = email_title
    msg["From"] = formataddr((display_name, SENDER_EMAIL))
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
    ses_client,
    email_title,
    template_content,
    row,
    display_name,
    file_ids=None,
    is_generate_certificate=False,
    run_id=None,
):
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
            email_title, formatted_content, recipient_email, display_name
        )

        attach_files_to_message(msg, file_ids)
        logger.info("Will generate certificate: %s", str(is_generate_certificate))
        certificate_path = None
        if is_generate_certificate:
            participant_name = row.get("Name")
            event_text = row.get("EventText")
            certificate_path = generate_certificate(
                run_id, participant_name, event_text
            )

            # 將證明文件附加到電子郵件
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

            # 成功發送郵件後刪除證書檔案
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

    # 發送郵件失敗後也刪除證書檔案
    if certificate_path:
        try:
            Path(certificate_path).unlink()
        except Exception as e:
            logger.error("Failed to delete certificate file: %s", e)

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
    is_generate_certificate=False,
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
    :param is_generate_certificate: Boolean flag indicating whether to generate a certificate.
    :return: Status and email ID of the email sending operation.
    """
    logger.info("Row data: %s", row)
    if not re.match(r"[^@]+@[^@]+\.[^@]+", recipient_email):
        logger.warning("Invalid email address provided: %s", recipient_email)
        return "FAILED", email_id

    sent_time, status = send_email(
        ses_client,
        email_title,
        template_content,
        row,
        display_name,
        file_ids,
        is_generate_certificate,
        run_id,
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


def generate_certificate(run_id: str, participant_name: str, event_text: str) -> str:

    def get_rect(coord: Tuple[int, int], width: int, height: int) -> fitz.Rect:
        return fitz.Rect(coord[0], coord[1], coord[0] + width, coord[1] + height)

    def get_font(is_ascii: bool) -> fitz.Font:
        font_name = "AmazonEmber_Rg.ttf" if is_ascii else "NotoSansTC-Regular.ttf"
        return fitz.Font(fontfile=str(Path(__file__).parent / "fonts" / font_name))

    try:
        # Prepare file paths
        template_path = (
            Path("/tmp") / Path(CERTIFICATE_TEMPLATE_FILE_S3_OBJECT_KEY).name
        )
        output_path = (
            Path("/tmp")
            / f"{run_id}_{participant_name.replace(' ', '_')}_certificate.pdf"
        )

        # Check if the template already exists in /tmp, if not, download it
        if not template_path.exists():
            try:
                template_content = read_file_from_s3(
                    PRIVATE_BUCKET_NAME, CERTIFICATE_TEMPLATE_FILE_S3_OBJECT_KEY
                )
                template_path.write_bytes(template_content)
            except Exception as e:
                logger.error("Error reading template file from S3: %s", e)
                raise

        # Generate certificate
        try:
            with fitz.open(str(template_path)) as doc:
                page = doc[0]
                tw = fitz.TextWriter(page.rect)

                # Add participant name
                is_ascii = all(ord(char) < 128 for char in participant_name)
                tw.fill_textbox(
                    get_rect(COORD_NAME, 300, 300),
                    participant_name,
                    font=get_font(is_ascii),
                    fontsize=FONT_SIZE_NAME,
                    align=1,
                )

                # Add event text
                tw.fill_textbox(
                    get_rect(COORD_EVENT, 525, 350),
                    event_text,
                    font=get_font(True),
                    fontsize=FONT_SIZE_EVENT,
                    align=1,
                )

                tw.write_text(page)
                doc.save(str(output_path))
        except Exception as e:
            logger.error("Error generating certificate: %s", e)
            raise

        # Upload and clean up
        try:
            certificate_s3_object_key = f"runs/{run_id}/certificates/{output_path.name}"
            upload_file_to_s3(str(output_path), BUCKET_NAME, certificate_s3_object_key)
        except Exception as e:
            logger.error("Error uploading file to S3: %s", e)
            raise

        logger.info(
            "Certificate generated and uploaded to S3: %s", certificate_s3_object_key
        )
        return str(output_path)
    except Exception as e:
        logger.error("Failed to generate certificate: %s", e)
        raise
