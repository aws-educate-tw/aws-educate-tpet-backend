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

    def list_campaigns(self) -> list[dict]:
        """List all campaigns from DynamoDB with pagination."""
        try:
            items = []
            query_kwargs = {
                "KeyConditionExpression": Key("cohort").eq(self.campaign_cohort),
                "ScanIndexForward": False,
            }

            while True:
                response = self.table.query(**query_kwargs)
                items.extend(response.get("Items", []))

                last_evaluated_key = response.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            return items
        except ClientError as e:
            logger.error("Error listing campaigns: %s", e)
            raise
