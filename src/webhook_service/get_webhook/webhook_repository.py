import logging
import os

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WebhookRepository:
    def __init__(self):
        """
        Initialize the repository with the DynamoDB table.
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

    def get_item(self, webhook_id):
        """
        Get a webhook item from the DynamoDB table.
        """
        webhook_details = self.table.get_item(Key={"webhook_id": webhook_id})

        if "Item" not in webhook_details:
            return None

        return webhook_details.get("Item")
    
