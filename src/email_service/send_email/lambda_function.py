import logging
import os
import uuid

import boto3
import time_util
from data_util import convert_float_to_decimal
from dynamodb import save_to_dynamodb
from s3 import get_template, read_sheet_data_from_s3
from ses import process_email
from sqs import delete_sqs_message, process_sqs_message

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
    run_id, template_file_id, spreadsheet_id, display_name, rows
):
    """
    Save each row of email data to DynamoDB with a status of 'PENDING'.

    :param run_id: The run ID for tracking the email sending operation.
    :param template_file_id: File ID of the email template.
    :param spreadsheet_id: File ID of the spreadsheet.
    :param display_name: Display name of the sender.
    :param rows: List of dictionaries, each containing email and other placeholder data.
    """
    for row in rows:
        email_id = str(uuid.uuid4().hex)
        row = convert_float_to_decimal(row)
        created_at = time_util.get_current_utc_time()
        logger.info("Converted row data: %s", row)
        save_to_dynamodb(
            run_id=run_id,
            email_id=email_id,
            display_name=display_name,
            status="PENDING",
            recipient_email=row.get("Email"),
            template_file_id=template_file_id,
            spreadsheet_file_id=spreadsheet_id,
            created_at=created_at,
            row_data=row,
        )


def fetch_and_process_pending_emails(
    run_id,
    email_title,
    template_content,
    display_name,
    template_file_id,
    spreadsheet_id,
    attachment_file_ids,
    is_generate_certificate,
):
    """
    Fetch emails with 'PENDING' status from DynamoDB and process them.

    :param run_id: The run ID for tracking the email sending operation.
    :param email_title: Title of the email to be sent.
    :param template_content: The HTML content of the email template.
    :param display_name: Display name of the sender.
    :param template_file_id: File ID of the email template.
    :param spreadsheet_id: File ID of the spreadsheet.
    :param attachment_file_ids: List of file IDs for attachments.
    :param is_generate_certificate: Boolean flag indicating whether to generate a certificate.
    """
    pending_emails = table.query(
        IndexName="run_id-status-gsi",
        KeyConditionExpression=boto3.dynamodb.conditions.Key("run_id").eq(run_id)
        & boto3.dynamodb.conditions.Key("status").eq("PENDING"),
    )

    ses_client = boto3.client("ses", region_name="ap-northeast-1")
    for item in pending_emails["Items"]:
        recipient_email = item["recipient_email"]
        email_id = item["email_id"]
        row = item.get("row_data")
        created_at = item.get("created_at")
        process_email(
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
            attachment_file_ids,
            is_generate_certificate,
        )


def lambda_handler(event, context):
    """
    AWS Lambda handler function to process SQS messages and handle email sending.

    :param event: The event data from SQS.
    :param context: The runtime information of the Lambda function.
    """
    for record in event["Records"]:
        try:
            msg = process_sqs_message(record)
            run_id = msg["run_id"]
            is_generate_certificate = msg.get("is_generate_certificate", False)
            # Check if the run_id already exists in DynamoDB
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key("run_id").eq(
                    run_id
                )
            )
            if response["Count"] == 0:
                # Run ID does not exist, save all emails to DynamoDB with PENDING status
                template_info = get_file_info(msg["template_file_id"])
                template_s3_key = template_info["s3_object_key"]

                spreadsheet_info = get_file_info(msg["spreadsheet_id"])
                spreadsheet_s3_key = spreadsheet_info["s3_object_key"]
                data, _ = read_sheet_data_from_s3(spreadsheet_s3_key)
                logger.info("Read sheet data from S3: %s", data)

                save_emails_to_dynamodb(
                    run_id,
                    msg["template_file_id"],
                    msg["spreadsheet_id"],
                    msg["display_name"],
                    data,
                )

            template_content = get_template(template_s3_key)
            fetch_and_process_pending_emails(
                run_id,
                msg["email_title"],
                template_content,
                msg["display_name"],
                msg["template_file_id"],
                msg["spreadsheet_id"],
                msg["attachment_file_ids"],
                is_generate_certificate,
            )
            logger.info("Processed all emails for run_id: %s", run_id)
        except Exception as e:
            logger.error("Error processing message: %s", e)
        finally:
            if SQS_QUEUE_URL:
                try:
                    delete_sqs_message(sqs_client, SQS_QUEUE_URL, msg["receipt_handle"])
                    logger.info("Deleted message from SQS: %s", msg["receipt_handle"])
                except Exception as e:
                    logger.error("Error deleting SQS message: %s", e)
            else:
                logger.error("SQS_QUEUE_URL is not available: %s", SQS_QUEUE_URL)
