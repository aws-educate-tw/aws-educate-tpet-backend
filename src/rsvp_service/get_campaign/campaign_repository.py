import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CampaignRepository:
    """Repository class for managing Campaign table operations in DynamoDB"""

    def __init__(self):
        """Initialize the repository with the campaigns table."""
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("CAMPAIGN_TABLE"))

    def get_campaign_by_id(self, campaign_id: str) -> dict | None:
        """Get a campaign by its ID."""
        try:
            response = self.table.get_item(Key={"campaign_id": campaign_id})
            return response.get("Item")
        except ClientError as e:
            logger.error("Error getting campaign by ID: %s", e)
            raise

    def list_campaigns(self) -> list[dict]:
        """List all campaigns from DynamoDB with pagination."""
        try:
            items = []
            scan_kwargs = {}

            while True:
                response = self.table.scan(**scan_kwargs)
                items.extend(response.get("Items", []))

                last_evaluated_key = response.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break
                scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

            return items
        except ClientError as e:
            logger.error("Error listing campaigns: %s", e)
            raise
