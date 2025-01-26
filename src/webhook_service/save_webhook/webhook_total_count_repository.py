import logging
import os

import boto3  # type: ignore # pylint: disable=import-error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WebhookIncrementCountRepository:
    """Repository for incrementing the total count of webhooks."""

    def __init__(self):
        """
        Initialize the repository with the DynamoDB table.
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("DYNAMODB_TABLE_TOTAL_COUNT"))

    def increment_total_count(self, webhook_type: str) -> int:
        """
        Increment the total count for a webhook_type atomically and return the new total.
        """
        try:
            response = self.table.update_item(
                Key={"webhook_type": webhook_type},
                UpdateExpression="ADD total_count :increment",
                ExpressionAttributeValues={":increment": 1},
                ReturnValues="UPDATED_NEW",
            )
            new_total = response["Attributes"]["total_count"]
            logger.info("Updated total count for %s: %s", webhook_type, new_total)
            return new_total
        except Exception as e:
            logger.error("Error updating counter for %s, %s", webhook_type, str(e))
            raise
