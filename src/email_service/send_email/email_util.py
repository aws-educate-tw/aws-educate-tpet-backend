import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from current_user_util import current_user_util
from s3 import download_file_content

from file_service import FileService

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize FileService
file_service = FileService()

# Constants
SENDER_EMAIL_DOMAIN = "aws-educate.tw"
CHARSET = "utf-8"


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
