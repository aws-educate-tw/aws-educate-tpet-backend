"""
This module provides a repository class for interacting with a DynamoDB table
to manage webhook items.
"""
import logging
import os

import boto3  # type: ignore # pylint: disable=import-error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WebhookRepository:
    """
    A repository class to interact with the DynamoDB table storing webhook details.

    Attributes:
        dynamodb (boto3.resource): A DynamoDB resource for interacting with the database.
        table (boto3.Table): The DynamoDB table instance to perform CRUD operations.
    """

    def __init__(self):
        """
        Initialize the WebhookRepository with a DynamoDB table resource.
        The table name is retrieved from the 'DYNAMODB_TABLE' environment variable.
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

    def get_item(self, webhook_id):
        """
        Retrieve a webhook item from the DynamoDB table.

        Args:
            webhook_id (str): The unique identifier for the webhook item to retrieve.

        Returns:
            dict: The webhook details if found, otherwise None.
        """
        webhook_details = self.table.get_item(Key={"webhook_id": webhook_id})

        if "Item" not in webhook_details:
            return None

        return webhook_details