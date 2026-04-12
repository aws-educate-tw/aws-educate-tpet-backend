import logging
import os

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CampaignRepository:
    """Repository class for managing Campaign table operations in DynamoDB"""

    def __init__(self):
        """Initialize the repository with the campaigns table."""
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("CAMPAIGN_TABLE"))
        self.campaign_cohort = "8"

    def get_campaign_by_id(self, campaign_id: str) -> dict | None:
        """Get a campaign by its ID."""
        try:
            response = self.table.query(
                KeyConditionExpression=Key("cohort").eq(self.campaign_cohort)
                & Key("campaign_id_created_at").begins_with(f"{campaign_id}_"),
                ScanIndexForward=False,
                Limit=1,
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except ClientError as e:
            logger.error("Error getting campaign by ID: %s", e)
            raise
