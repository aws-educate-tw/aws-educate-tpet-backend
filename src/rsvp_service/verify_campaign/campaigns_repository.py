"""
Repository for querying the Campaigns DynamoDB table.
"""

import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CampaignsRepository:
    """Repository for reading campaigns from DynamoDB."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.environ["DYNAMODB_TABLE"])

    def get_campaign_by_id(self, campaign_id: str) -> dict | None:
        """
        Fetch a campaign item by its primary key.

        :param campaign_id: The campaign_id to look up.
        :return: The item dict, or None if not found.
        :raises ClientError: Propagated so the caller can return a 500.
        """
        try:
            response = self.table.get_item(
                Key={"campaign_id": campaign_id},
                ProjectionExpression="campaign_id, campaign_name, is_active",
            )
            return response.get("Item")
        except ClientError as e:
            logger.error(
                "Error fetching campaign %s: %s", campaign_id, e
            )
            raise
