import logging
import os

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CampaignRunRepository:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("CAMPAIGN_RUN_TABLE"))

    def query_by_campaign_id(self, campaign_id: str) -> list[dict]:
        """Query all campaign run items by campaign ID."""
        try:
            query_kwargs = {
                "KeyConditionExpression": Key("campaign_id").eq(campaign_id),
            }
            items = []

            while True:
                response = self.table.query(**query_kwargs)
                items.extend(response.get("Items", []))

                last_evaluated_key = response.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            return items
        except ClientError as e:
            logger.error("Error querying campaign runs: %s", e)
            raise
