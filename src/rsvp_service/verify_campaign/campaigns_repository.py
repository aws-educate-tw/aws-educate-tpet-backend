"""
Repository for querying the Campaigns DynamoDB table.
"""

import logging
import os

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CampaignsRepository:
    """Repository for reading campaigns from DynamoDB."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.environ["DYNAMODB_TABLE"])
        self.cohort = os.environ.get("COHORT", "8")

    def get_campaign_by_id(self, campaign_id: str) -> dict | None:
        """
        Find a campaign by campaign_id.

        Since the table PK is `cohort` and SK is `campaign_id_created_at`
        (format: "{campaign_id}-{created_at}"), we Query with cohort as the
        partition key and begins_with(campaign_id) as the SK condition.

        :param campaign_id: The campaign_id to look up.
        :return: The item dict, or None if not found.
        :raises ClientError: Propagated so the caller can return a 500.
        """
        try:
            response = self.table.query(
                KeyConditionExpression=Key("cohort").eq(self.cohort)
                & Key("campaign_id_created_at").begins_with(campaign_id),
                ProjectionExpression="campaign_id, campaign_name, is_active",
                Limit=1,
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except ClientError as e:
            logger.error(
                "Error querying campaign %s: %s", campaign_id, e
            )
            raise
