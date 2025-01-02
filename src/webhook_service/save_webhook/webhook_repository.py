"""
This module contains the repository for saving webhook data to a table named webhook in DynamoDB. 
"""
import logging
import os

import boto3  # type: ignore # pylint: disable=import-error
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WebhookRepository:
    """ Repository for saving webhooks to DynamoDB. """
    def __init__(self):
        """
        Initialize the repository with the DynamoDB table.
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

    def save_data(self, item: dict) -> dict:
        """
        Save a webhook item to the database.

        :param item: The webhook item to save.
        :return: The response from DynamoDB.    
        """
        try:
            response = self.table.put_item(Item=item)
            logger.info("Webhook saved: %s", item)
            return response
        except Exception as e:
            logger.error("Error saving webhook: %s", str(e))
            raise
        