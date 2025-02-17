"""
This module contains the repository for saving webhook data to a table named webhook in DynamoDB.
"""

import logging
import os
from typing import Any

import boto3  # type: ignore # pylint: disable=import-error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WebhookRepository:
    """Repository for saving webhooks to DynamoDB."""

    def __init__(self):
        """
        Initialize the repository with the DynamoDB table.
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

    def get_webhook_details(self, webhook_id: str) -> dict[str, Any] | None:
        """
        Get a webhook item from the database.
        """
        try:
            response = self.table.get_item(Key={"webhook_id": webhook_id})
            item = response.get("Item")
            logger.info("Webhook details retrieved: %s", item)
            return item
        except Exception as e:
            logger.error("Error getting webhook details: %s", str(e))
            raise
