import logging
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from s3 import read_file_from_s3

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Constants
SENDER_EMAIL_DOMAIN = "aws-educate.tw"
CHARSET = "utf-8"
BUCKET_NAME = os.getenv("BUCKET_NAME")


def create_email_message(
    subject,
    formatted_content,
    recipient_email,
    display_name,
    reply_to,
    cc,
    bcc,
    sender_local_part,
):
    """
    Create an email message with the given title, content, recipient, and display name.

    :param email_title: Title of the email.
    :param formatted_content: Content of the email in HTML format.
    :param recipient_email: Email address of the recipient.
    :param display_name: Display name of the sender.
    :param reply_to: Reply-To email address.
    :param cc: List of CC email addresses.
    :param bcc: List of BCC email addresses.
    :param sender_local_part: Local part of the sender's email address.
    :return: A MIMEMultipart email message.
    """

    sender_email = f"{sender_local_part}@{SENDER_EMAIL_DOMAIN}"

    # Create a multipart/mixed parent container.
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = formataddr((display_name, sender_email))
    msg["To"] = recipient_email
    msg["Reply-To"] = reply_to

    if cc:
        msg["Cc"] = ", ".join(cc)
    if bcc:
        msg["Bcc"] = ", ".join(bcc)

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


def attach_files_to_message(msg, attachment_files):
    """
    Attach files to the email message.

    :param msg: The email message to attach files to.
    :param attachment_files: List of file info dicts stored in RUNS.attachment_files.
    """
    if not attachment_files:
        return

    logger.info("Processing file attachments.")
    for file_info in attachment_files:
        try:
            s3_object_key = file_info.get("s3_object_key")
            file_name = file_info.get("file_name")
            file_size = file_info.get("file_size")

            logger.info("Processing file: %s", file_name)

            if s3_object_key and file_name:
                # Read the file from S3 and attach it
                file_content = read_file_from_s3(BUCKET_NAME, s3_object_key)
                attachment = MIMEApplication(file_content)
                attachment.add_header(
                    "Content-Disposition", "attachment", filename=file_name
                )
                if file_size:
                    attachment.add_header("Content-Length", str(file_size))
                msg.attach(attachment)
                logger.info("Attached file: %s", file_name)
            else:
                logger.warning("File info incomplete: %s", file_info)
        except Exception as e:
            logger.error("Error processing file attachment %s: %s", file_info, e)
            # Continue to the next file rather than failing the entire email
