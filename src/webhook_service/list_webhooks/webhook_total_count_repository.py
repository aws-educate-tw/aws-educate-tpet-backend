"""
This module contains the repository for fetching from a table named webhook_total_count in DynamoDB.
"""

import logging
import os

import boto3  # type: ignore #pylint: disable=import-error

# Logger setup outside the class
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class WebhookTotalCountRepository:
    """ Repository for fetching total counts from DynamoDB. """
    def __init__(self):
        """
        Initialize the repository with the DynamoDB table.
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("DYNAMODB_TABLE_TOTAL_COUNT"))

    def get_total_count(self, webhook_type: str) -> int:
        """
        Get the total count of items for a specific webhook_type.
        
        :param webhook_type: The type of webhook to fetch the count for.
        :return: The total count of items for the given webhook_type.
        """
        try:
            response = self.table.get_item(Key={"webhook_type": webhook_type})
            total_count = response.get("Item", {}).get("total_count", 0)
            return int(total_count)
        except Exception as e:
            logger.error("Error fetching total count for %s: %s", webhook_type, str(e))
            raise