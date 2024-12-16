import logging
import os

import boto3

dynamodb = boto3.resource("dynamodb")
total_count_table = dynamodb.Table(os.getenv("DYNAMODB_TABLE_TOTAL_COUNT"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_total_count(webhook_type: str) -> int:
    """
    Get the total count of items for a specific webhook_type.
    """
    try:
        response = total_count_table.get_item(Key={"webhook_type": webhook_type})
        total_count = response.get("Item", {}).get("total_count", 0)
        return int(total_count)
    except Exception as e:
        logger.error(f"Error fetching total count for {webhook_type}: {str(e)}")
        raise