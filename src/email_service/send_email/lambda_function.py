import json
import logging
import os
import uuid

import boto3
import time_util
from data_util import convert_float_to_decimal
from dynamodb import save_to_dynamodb
from s3 import get_template, read_sheet_data_from_s3
from ses import process_email
from sqs import delete_sqs_message

from file_service import get_file_info

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

dynamodb = boto3.resource("dynamodb")
sqs_client = boto3.client("sqs")
table = dynamodb.Table(DYNAMODB_TABLE)


def lambda_handler(event, context):
    for record in event["Records"]:
        try:
            body = json.loads(record["body"])
            receipt_handle = record["receiptHandle"]
            template_file_id = body.get("template_file_id")
            spreadsheet_id = body.get("spreadsheet_file_id")
            email_title = body.get("email_title")
            display_name = body.get("display_name")
            run_id = body.get("run_id")
            attachment_file_ids = body.get("attachment_file_ids", [])

            logger.info("Processing message with run_id: %s", run_id)

            # Check if the run_id already exists in DynamoDB
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key("run_id").eq(
                    run_id
                )
            )
            if response["Count"] == 0:
                # Run ID does not exist, save all emails to DynamoDB with PENDING status
                template_info = get_file_info(template_file_id)
                template_s3_key = template_info["s3_object_key"]
                template_content = get_template(template_s3_key)

                spreadsheet_info = get_file_info(spreadsheet_id)
                spreadsheet_s3_key = spreadsheet_info["s3_object_key"]
                data, _ = read_sheet_data_from_s3(spreadsheet_s3_key)

                for row in data:
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

            # Fetch emails with PENDING status and process them
            pending_emails = table.query(
                IndexName="run_id-status-gsi",
                KeyConditionExpression=boto3.dynamodb.conditions.Key("run_id").eq(
                    run_id
                )
                & boto3.dynamodb.conditions.Key("status").eq("PENDING"),
            )

            ses_client = boto3.client("ses", region_name="ap-northeast-1")
            template_content = get_template(
                template_s3_key
            )  # Load the template content
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
                )
            logger.info("Processed all emails for run_id: %s", run_id)
        except Exception as e:
            logger.error("Error processing message: %s", e)
        finally:
            if SQS_QUEUE_URL:
                try:
                    delete_sqs_message(sqs_client, SQS_QUEUE_URL, receipt_handle)
                    logger.info("Deleted message from SQS: %s", receipt_handle)
                except Exception as e:
                    logger.error("Error deleting SQS message: %s", e)
            else:
                logger.error("SQS_QUEUE_URL is not available: %s", SQS_QUEUE_URL)
