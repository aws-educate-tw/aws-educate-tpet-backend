"""
This module contains the repository for fetching from a table named webhook in DynamoDB.
"""
import logging
import os

import boto3  # type: ignore #pylint: disable=import-error
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class WebhookRepository:
    """ Repository for fetching webhooks from DynamoDB. """
    def __init__(self):
        """
        Initialize the repository with the DynamoDB table.
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

    def get_data(self, webhook_type: str, sort_order: str = "ASC", start_key: int = 0, end_key: int = 0):
        """
        Get a list of webhooks for a specific webhook_type.
        :param webhook_type: The type of webhook to fetch.
        :param sort_order: The sort order for the items (either "ASC" or "DESC").
        :param start_key: The start key for pagination.
        :param end_key: The end key for pagination.
        :return: A list of webhook items.
        """
        try:
            # Query DynamoDB for the calculated range.
            # The order of sequence_number is the same as the ascending order of created_at.
            # So sorting by sequence_number is the same as sorting by created_at.
            # We only need to use webhook-webhook_type-sequence_number-gsi to sort here.
            response = self.table.query(
                IndexName="webhook-webhook_type-sequence_number-gsi",
                KeyConditionExpression=(
                    Key("webhook_type").eq(webhook_type) &
                    Key("sequence_number").between(start_key, end_key)
                ),
                ScanIndexForward=sort_order == "ASC"  # True for ASC, False for DESC
            )
            data = response.get("Items", [])
            return data
        except Exception as e:
            logger.error(
                "Error fetching webhooks for webhook_type: %s. Error: %s",
                webhook_type,
                str(e)
            )
            raise
