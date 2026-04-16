"""
Repository for creating campaigns in the DynamoDB Campaigns table.
"""

import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CampaignsRepository:
    """Repository for creating campaigns in DynamoDB."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.environ["DYNAMODB_TABLE"])

    def create_campaign(self, item: dict) -> None:
        """
        Write a new campaign item to DynamoDB.

        Uses ConditionExpression to guard against the (extremely unlikely)
        case of a UUID collision.

        :param item: Flat dict containing all campaign fields.
        :raises ClientError: Propagated so the caller can map it to an HTTP response.
        """
        try:
            self.table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(campaign_id_created_at)",
            )
            logger.info("Created campaign: %s", item.get("campaign_id"))
        except ClientError as e:
            logger.error(
                "Error creating campaign %s: %s",
                item.get("campaign_id"),
                e,
            )
            raise
