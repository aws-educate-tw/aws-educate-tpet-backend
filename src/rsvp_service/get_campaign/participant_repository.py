import logging
import os

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ParticipantRepository:
    """Repository class for managing Participant table operations in DynamoDB"""

    def __init__(self):
        """Initialize the repository with the participants table."""
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("PARTICIPANT_TABLE"))

    def query_by_run_id(self, run_id: str) -> list[dict]:
        """Query all participants for a specific run."""
        try:
            query_kwargs = {
                "KeyConditionExpression": Key("run_id").eq(run_id),
            }
            participants = []

            while True:
                response = self.table.query(**query_kwargs)
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
            logger.error("Error querying participants: %s", e)
            raise
