import logging
import os

import boto3

dynamodb = boto3.resource("dynamodb")

total_count_table = dynamodb.Table(os.getenv("DYNAMODB_TABLE_TOTAL_COUNT"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def increment_total_count(webhook_type: str) -> int:
    """
    Increment the total count for a webhook_type atomically and return the new total.
    """
    try:
        response = total_count_table.update_item(
            Key={"webhook_type": webhook_type},
            UpdateExpression="ADD total_count :increment",
            ExpressionAttributeValues={":increment": 1},
            ReturnValues="UPDATED_NEW"
        )
        new_total = response["Attributes"]["total_count"]
        logger.info(f"Updated total count for {webhook_type}: {new_total}")
        return new_total
    except Exception as e:
        logger.error(f"Error updating counter for {webhook_type}: {str(e)}")
        raise