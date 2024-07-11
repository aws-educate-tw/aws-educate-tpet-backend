import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)


def save_to_dynamodb(
    run_id,
    email_id,
    display_name,
    status,
    recipient_email,
    template_file_id,
    spreadsheet_file_id,
    created_at,
    sent_at=None,
    updated_at=None,
):
    try:

        item = {
            "run_id": run_id,
            "email_id": email_id,
            "display_name": display_name,
            "status": status,
            "recipient_email": recipient_email,
            "template_file_id": template_file_id,
            "spreadsheet_file_id": spreadsheet_file_id,
            "created_at": created_at,
            "updated_at": updated_at,
        }
        if sent_at:
            item["sent_at"] = sent_at
        table.put_item(Item=item)
        logger.info("Saved email record to DynamoDB: %s", email_id)
    except ClientError as e:
        logger.error("Error in save_to_dynamodb: %s", e)
    except Exception as e:
        logger.error("Error in save_to_dynamodb: %s", e)
        raise
