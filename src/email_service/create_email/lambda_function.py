import json
import logging
import os
import uuid

import boto3
import time_util
from current_user_util import current_user_util
from data_util import convert_float_to_decimal
from email_repository import EmailRepository
from s3 import read_sheet_data_from_s3
from sqs import delete_sqs_message, get_sqs_message

from file_service import FileService

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get environment variables
CREATE_EMAIL_SQS_QUEUE_URL = os.getenv(
    "CREATE_EMAIL_SQS_QUEUE_URL"
)  # Queue for receiving create email requests
SEND_EMAIL_SQS_QUEUE_URL = os.getenv(
    "SEND_EMAIL_SQS_QUEUE_URL"
)  # Queue for triggering email sending

# Initialize clients and services
sqs_client = boto3.client("sqs")
file_service = FileService()
email_repository = EmailRepository()


def create_email_item(run_id: str, email_data: dict, row_data: dict) -> dict:
    """
    Create an email item with the necessary data.

    :param run_id: The run ID for tracking the email operation
    :param email_data: Dictionary containing email metadata
    :param row_data: Dictionary containing recipient data and template variables
    :return: Created email item dictionary
    """
    email_id = str(uuid.uuid4().hex)
    row_data = convert_float_to_decimal(row_data)
    created_at = time_util.get_current_utc_time()

    return {
        "run_id": run_id,
        "email_id": email_id,
        "subject": email_data["subject"],
        "display_name": email_data["display_name"],
        "template_file_id": email_data["template_file_id"],
        "spreadsheet_file_id": email_data.get("spreadsheet_file_id"),
        "attachment_file_ids": email_data.get("attachment_file_ids", []),
        "status": "PENDING",
        "recipient_email": row_data.get("Email"),
        "row_data": row_data,
        "created_at": created_at,
        "is_generate_certificate": email_data.get("is_generate_certificate", False),
        "sender_id": email_data["sender_id"],
        "sender_username": current_user_util.get_current_user_info().get("username"),
        "reply_to": email_data.get("reply_to"),
        "sender_local_part": email_data.get("sender_local_part"),
        "cc": email_data.get("cc"),
        "bcc": email_data.get("bcc"),
    }


def send_to_email_queue(email_item: dict) -> None:
    """
    Send email item to the send email queue.

    :param email_item: The email item to be sent
    """
    message = {
        "run_id": email_item["run_id"],
        "email_id": email_item["email_id"],
        "recipient_email": email_item["recipient_email"],
        "subject": email_item["subject"],
        "template_file_id": email_item["template_file_id"],
        "display_name": email_item["display_name"],
        "row_data": email_item["row_data"],
        "attachment_file_ids": email_item["attachment_file_ids"],
        "is_generate_certificate": email_item["is_generate_certificate"],
        "sender_id": email_item["sender_id"],
        "reply_to": email_item.get("reply_to"),
        "sender_local_part": email_item.get("sender_local_part"),
        "cc": email_item.get("cc"),
        "bcc": email_item.get("bcc"),
        "access_token": current_user_util.get_current_user_access_token(),
    }

    try:
        response = sqs_client.send_message(
            QueueUrl=SEND_EMAIL_SQS_QUEUE_URL, MessageBody=json.dumps(message)
        )
        logger.info(
            "Successfully queued email %s for sending: %s",
            email_item["email_id"],
            response["MessageId"],
        )
    except Exception as e:
        logger.error(
            "Failed to queue email %s for sending: %s", email_item["email_id"], str(e)
        )
        # Update email status to FAILED if we couldn't queue it
        email_repository.update_email_status(
            run_id=email_item["run_id"],
            email_id=email_item["email_id"],
            status="FAILED",
        )
        raise


def process_recipients(sqs_message: dict) -> list[dict]:
    """
    Process recipients based on the source type (SPREADSHEET or DIRECT).

    :param sqs_message: The SQS message containing recipient information
    :return: List of recipient data dictionaries
    """
    recipient_source = sqs_message.get("recipient_source", "SPREADSHEET")

    if recipient_source == "SPREADSHEET":
        spreadsheet_info = file_service.get_file_info(
            sqs_message["spreadsheet_file_id"],
            current_user_util.get_current_user_access_token(),
        )
        spreadsheet_s3_object_key = spreadsheet_info["s3_object_key"]
        sheet_data, _ = read_sheet_data_from_s3(spreadsheet_s3_object_key)
        logger.info("Read sheet data from S3: %s", sheet_data)
        return sheet_data
    else:  # DIRECT mode
        sheet_data = []
        for recipient in sqs_message["recipients"]:
            recipient_data = {
                "Email": recipient["email"],
                **recipient["template_variables"],
            }
            sheet_data.append(recipient_data)
        logger.info("Processed direct recipients data: %s", sheet_data)
        return sheet_data


def lambda_handler(event, context):
    """
    AWS Lambda handler function to process email creation requests.

    :param event: The event data from SQS
    :param context: The runtime information of the Lambda function
    """
    logger.info("Lambda triggered with event: %s", event)

    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    for record in event["Records"]:
        try:
            sqs_message = get_sqs_message(record)
            access_token = sqs_message["access_token"]

            # Set the current user information
            current_user_util.set_current_user_by_access_token(access_token)

            # Check if emails already exist for this run_id
            response = email_repository.query_emails(
                run_id=sqs_message["run_id"],
                limit=1,
                last_evaluated_key=None,
                sort_order="ASC",
            )

            # If no emails exist, process recipients and create email items
            if response["Count"] == 0:
                # Process recipients and create email items
                recipients_data = process_recipients(sqs_message)

                for row_data in recipients_data:
                    # Create and save email item
                    email_item = create_email_item(
                        sqs_message["run_id"], sqs_message, row_data
                    )
                    email_repository.save_email(email_item)

                    # Queue the email for sending
                    send_to_email_queue(email_item)

                logger.info(
                    "Successfully processed all recipients for run_id: %s",
                    sqs_message["run_id"],
                )
            else:
                logger.info(
                    "Emails already exist for run_id: %s. Skipping creation.",
                    sqs_message["run_id"],
                )

        except Exception as e:
            logger.error("Error processing message: %s", e)
            raise
        finally:
            if CREATE_EMAIL_SQS_QUEUE_URL:
                try:
                    delete_sqs_message(
                        sqs_client,
                        CREATE_EMAIL_SQS_QUEUE_URL,
                        sqs_message["receipt_handle"],
                    )
                    logger.info(
                        "Deleted message from SQS: %s", sqs_message["receipt_handle"]
                    )
                except Exception as e:
                    logger.error("Error deleting SQS message: %s", e)
            else:
                logger.error(
                    "CREATE_EMAIL_SQS_QUEUE_URL is not available: %s",
                    CREATE_EMAIL_SQS_QUEUE_URL,
                )
