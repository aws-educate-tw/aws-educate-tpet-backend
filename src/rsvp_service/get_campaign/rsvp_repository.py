import logging
import os

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RsvpRepository:
    """Repository class for managing RSVP-related data in DynamoDB"""

    def __init__(self):
        """Initialize the repository with a DynamoDB table name."""
        self.dynamodb = boto3.resource("dynamodb")
        self.campaigns_table = self.dynamodb.Table(os.getenv("CAMPAIGNS_TABLE"))
        self.runs_table = self.dynamodb.Table(os.getenv("RUNS_CAMPAIGNS_MAPPING_TABLE"))
        self.participants_table = self.dynamodb.Table(os.getenv("PARTICIPANTS_TABLE"))

    def get_campaign_by_id(self, campaign_id: str) -> dict | None:
        """Get a campaign by its ID."""
        try:
            response = self.campaigns_table.get_item(Key={"campaign_id": campaign_id})
            return response.get("Item")
        except ClientError as e:
            logger.error("Error getting campaign by ID: %s", e)
            raise

    def query_all_campaign_run_items(self, campaign_id: str) -> list[dict]:
        """Query all campaign run configuration items from DynamoDB."""
        try:
            query_kwargs = {
                "KeyConditionExpression": Key("campaign_id").eq(campaign_id),
            }
            run_items = []

            while True:
                response = self.runs_table.query(**query_kwargs)
                run_items.extend(response.get("Items", []))

                last_evaluated_key = response.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            return run_items
        except ClientError as e:
            logger.error("Error querying campaign run items: %s", e)
            raise

    def query_all_participants_by_run(self, run_id: str) -> list[dict]:
        """Query all participants for a specific run."""
        try:
            query_kwargs = {
                "KeyConditionExpression": Key("run_id").eq(run_id),
            }
            participants = []

            while True:
                response = self.participants_table.query(**query_kwargs)
                items = response.get("Items", [])

                for item in items:
                    participants.append(
                        {
                            "participant_id": item.get("participant_id"),
                            "email_id": item.get("email_id"),
                            "rsvp_status": item.get("rsvp_status"),
                            "name": item.get("name"),
                            "created_at": item.get("created_at"),
                            "updated_at": item.get("updated_at"),
                        }
                    )

                last_evaluated_key = response.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            return participants
        except ClientError as e:
            logger.error("Error querying participants by run: %s", e)
            raise
