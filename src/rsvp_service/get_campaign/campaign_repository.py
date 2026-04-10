import logging
import os

import boto3
from boto3.dynamodb.conditions import Attr, Key
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
            query_kwargs = {
                "KeyConditionExpression": Key("cohort").eq(self.campaign_cohort),
                "FilterExpression": Attr("campaign_id").eq(campaign_id),
                "ScanIndexForward": False,
            }

            while True:
                response = self.table.query(**query_kwargs)
                items = response.get("Items", [])
                if items:
                    return items[0]

                last_evaluated_key = response.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            return None
        except ClientError as e:
            logger.error("Error getting campaign by ID: %s", e)
            raise
