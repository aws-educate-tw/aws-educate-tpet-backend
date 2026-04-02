"""
Repository for importing participants into the DynamoDB participants table.
"""

import logging
import os

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

GSI_NAME = "participant-campaign_participant_uniq_handle-created_at-gsi"


class ParticipantsRepository:
    """Repository for managing participants in DynamoDB."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.environ["DYNAMODB_TABLE_PARTICIPANTS"])

    def find_existing_participant_id(
        self, campaign_participant_uniq_handle: str
    ) -> str | None:
        """
        Query the GSI to check whether a participant with the same email
        already exists under this campaign (across any run).

        :param campaign_participant_uniq_handle: "{campaign_id}#{email}"
        :return: The existing participant_id, or None if not found.
        :raises ClientError: Propagated so the caller can return a 500.
        """
        try:
            response = self.table.query(
                IndexName=GSI_NAME,
                KeyConditionExpression=Key("campaign_participant_uniq_handle").eq(
                    campaign_participant_uniq_handle
                ),
                ProjectionExpression="participant_id",
                Limit=1,
            )
            items = response.get("Items", [])
            if items:
                return items[0]["participant_id"]
            return None
        except ClientError as e:
            logger.error(
                "Error querying GSI for handle %s: %s",
                campaign_participant_uniq_handle,
                e,
            )
            raise

    def put_participant(self, item: dict) -> None:
        """
        Write a participant item to DynamoDB.

        :param item: Full participant item dict.
        :raises ClientError: Propagated so the caller can return a 500.
        """
        try:
            self.table.put_item(Item=item)
            logger.info(
                "Written participant run_id=%s participant_id=%s",
                item.get("run_id"),
                item.get("participant_id"),
            )
        except ClientError as e:
            logger.error(
                "Error writing participant run_id=%s participant_id=%s: %s",
                item.get("run_id"),
                item.get("participant_id"),
                e,
            )
            raise
