import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)


def save_to_dynamodb(item: dict):
    try:
        required_keys = [
            "run_id",
            "email_id",
            "display_name",
            "status",
            "recipient_email",
            "template_file_id",
            "spreadsheet_file_id",
            "row_data",
            "created_at",
        ]
        for key in required_keys:
            if key not in item:
                raise ValueError(f"Missing required key: {key}")

        table.put_item(Item=item)
        logger.info("Saved email record to DynamoDB: %s", item.get("email_id"))
    except ClientError as e:
        logger.error("Error in save_to_dynamodb: %s", e)
    except Exception as e:
        logger.error("Error in save_to_dynamodb: %s", e)
        raise
