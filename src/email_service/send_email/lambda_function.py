import logging
import os
import re

from current_user_util import current_user_util
from email_repository import EmailRepository
from run_repository import RunRepository
from s3 import read_html_template_file_from_s3
from ses import send_email
from sqs import delete_sqs_message, get_sqs_message

from file_service import FileService

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get environment variables
SEND_EMAIL_SQS_QUEUE_URL = os.getenv("SEND_EMAIL_SQS_QUEUE_URL")
BUCKET_NAME = os.getenv("BUCKET_NAME")

# Initialize clients and services
file_service = FileService()
email_repository = EmailRepository()
run_repository = RunRepository()


def process_email(email_data: dict) -> None:
    """
    Process email sending for a given email record.

    :param email_data: Dictionary containing complete email data including recipient and template information
    """
    recipient_email = email_data.get("recipient_email")
    email_id = email_data.get("email_id")
    run_id = email_data.get("run_id")

    if not re.match(r"[^@]+@[^@]+\.[^@]+", recipient_email):
        logger.warning("Invalid email address provided: %s", recipient_email)
        email_repository.update_email_status(
            run_id=run_id, email_id=email_id, status="FAILED"
        )
        return

    try:
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
        _, status = send_email(
            email_data.get("subject"),
            template_content,
            email_data.get("row_data"),
            email_data.get("display_name"),
            email_data.get("reply_to"),
            email_data.get("sender_local_part"),
            email_data.get("attachment_file_ids"),
            email_data.get("is_generate_certificate"),
            run_id,
            email_data.get("cc"),
            email_data.get("bcc"),
        )

        # Update the item in DynamoDB
        email_repository.update_email_status(
            run_id=run_id, email_id=email_id, status=status
        )

        # Increment success count if email was sent successfully
        if status == "SUCCESS":
            run_repository.increment_success_email_count(run_id)

    except Exception as e:
        logger.error("Error processing email %s: %s", email_id, str(e))
        email_repository.update_email_status(
            run_id=run_id, email_id=email_id, status="FAILED"
        )
        raise


def lambda_handler(event, context):
    """
    AWS Lambda handler function to process SQS messages for sending emails.

    :param event: The event data from SQS
    :param context: The runtime information of the Lambda function
    """
    # Log the start of Lambda execution and incoming event details
    logger.info("Lambda triggered with event: %s", event)

    # Identify if the incoming event is a prewarm request
    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    for record in event["Records"]:
        try:
            sqs_message = get_sqs_message(record)
            access_token = sqs_message["access_token"]

            # Set the current user information
            current_user_util.set_current_user_by_access_token(access_token)

            # Process the email
            process_email(sqs_message)

            logger.info(
                "Successfully processed email for run_id: %s", sqs_message.get("run_id")
            )

        except Exception as e:
            logger.error("Error processing message: %s", e)
            raise
        finally:
            if SEND_EMAIL_SQS_QUEUE_URL:
                try:
                    delete_sqs_message(
                        SEND_EMAIL_SQS_QUEUE_URL,
                        sqs_message["receipt_handle"],
                    )
                    logger.info(
                        "Deleted message from SQS: %s", sqs_message["receipt_handle"]
                    )
                except Exception as e:
                    logger.error("Error deleting SQS message: %s", e)
            else:
                logger.error(
                    "SQS_QUEUE_URL is not available: %s", SEND_EMAIL_SQS_QUEUE_URL
                )
