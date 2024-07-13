import logging
import os
import uuid

import boto3
import time_util
from data_util import convert_float_to_decimal
from dynamodb import save_to_dynamodb
from s3 import read_sheet_data_from_s3
from ses import process_email
from sqs import delete_sqs_message, get_sqs_message

from file_service import get_file_info

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get environment variables for DynamoDB table and SQS queue URL
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

# Initialize DynamoDB resource and SQS client
dynamodb = boto3.resource("dynamodb")
sqs_client = boto3.client("sqs")
table = dynamodb.Table(DYNAMODB_TABLE)


def save_emails_to_dynamodb(
    sqs_message: dict,
    rows: list[dict[str, any]],
):
    """
    Save each row of email data to DynamoDB with a status of 'PENDING'.

    :param sqs_message: A dictionary containing the details for processing the email.
        It should include the following keys:
        - run_id: The run ID for tracking the email sending operation.
        - subject: Title of the email to be sent.
        - display_name: Display name of the sender.
        - template_file_id: File ID of the email template.
        - spreadsheet_file_id: File ID of the spreadsheet.
        - attachment_file_ids: List of file IDs for attachments.
        - is_generate_certificate: Boolean flag indicating whether to generate a certificate.
    :param rows: List of dictionaries, each containing email and other placeholder data.
    """
    for row in rows:
        email_id = str(uuid.uuid4().hex)
        row = convert_float_to_decimal(row)
        created_at = time_util.get_current_utc_time()
        logger.info("Converted row data: %s", row)

        # Create the item dictionary
        item = {
            "run_id": sqs_message["run_id"],
            "email_id": email_id,
            "subject": sqs_message["subject"],
            "display_name": sqs_message["display_name"],
            "template_file_id": sqs_message["template_file_id"],
            "spreadsheet_file_id": sqs_message["spreadsheet_file_id"],
            "attachment_file_ids": sqs_message["attachment_file_ids"],
            "status": "PENDING",
            "recipient_email": row.get("Email"),
            "row_data": row,
            "created_at": created_at,
            "is_generate_certificate": sqs_message["is_generate_certificate"],
        }

        # Save to DynamoDB
        save_to_dynamodb(item)


def fetch_and_process_pending_emails(
    sqs_message: dict,
):
    """
    Fetch emails with 'PENDING' status from DynamoDB and process them.

    :param sqs_message: A dictionary containing the details for processing the email.
        It should include the following keys:
        - run_id: The run ID for tracking the email sending operation.
        - subject: Title of the email to be sent.
        - display_name: Display name of the sender.
        - template_file_id: File ID of the email template.
        - spreadsheet_file_id: File ID of the spreadsheet.
        - attachment_file_ids: List of file IDs for attachments.
        - is_generate_certificate: Boolean flag indicating whether to generate a certificate.
    """
    pending_emails = table.query(
        IndexName="run_id-status-gsi",
        KeyConditionExpression=boto3.dynamodb.conditions.Key("run_id").eq(
            sqs_message["run_id"]
        )
        & boto3.dynamodb.conditions.Key("status").eq("PENDING"),
    )

    for item in pending_emails["Items"]:
        email_data = {
            "run_id": sqs_message["run_id"],
            "email_id": item["email_id"],
            "subject": sqs_message["subject"],
            "display_name": sqs_message["display_name"],
            "template_file_id": sqs_message["template_file_id"],
            "spreadsheet_file_id": sqs_message["spreadsheet_file_id"],
            "attachment_file_ids": sqs_message["attachment_file_ids"],
            "is_generate_certificate": sqs_message["is_generate_certificate"],
            "created_at": item.get("created_at"),
        }
        row = item.get("row_data")
        process_email(email_data, row)


def lambda_handler(event, context):
    """
    AWS Lambda handler function to process SQS messages and handle email sending.

    :param event: The event data from SQS.
    :param context: The runtime information of the Lambda function.
    """
    for record in event["Records"]:
        try:
            sqs_message = get_sqs_message(record)
            # Check if the run_id already exists in DynamoDB
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key("run_id").eq(
                    sqs_message["run_id"]
                )
            )
            if response["Count"] == 0:
                # Run ID does not exist, save all emails to DynamoDB with PENDING status
                spreadsheet_info = get_file_info(sqs_message["spreadsheet_file_id"])
                spreadsheet_s3_object_key = spreadsheet_info["s3_object_key"]
                sheet_data, _ = read_sheet_data_from_s3(spreadsheet_s3_object_key)
                logger.info("Read sheet data from S3: %s", sheet_data)
                save_emails_to_dynamodb(
                    sqs_message,
                    sheet_data,
                )

            fetch_and_process_pending_emails(sqs_message)
            logger.info("Processed all emails for run_id: %s", sqs_message["run_id"])
        except Exception as e:
            logger.error("Error processing message: %s", e)
        finally:
            if SQS_QUEUE_URL:
                try:
                    delete_sqs_message(
                        sqs_client, SQS_QUEUE_URL, sqs_message["receipt_handle"]
                    )
                    logger.info(
                        "Deleted message from SQS: %s", sqs_message["receipt_handle"]
                    )
                except Exception as e:
                    logger.error("Error deleting SQS message: %s", e)
            else:
                logger.error("SQS_QUEUE_URL is not available: %s", SQS_QUEUE_URL)
