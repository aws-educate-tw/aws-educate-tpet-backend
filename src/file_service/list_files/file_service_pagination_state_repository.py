import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLE_NAME = "file_service_pagination_state"


class FileServicePaginationStateRepository:
    """Repository class for managing pagination state in DynamoDB"""

    def __init__(self):
        """
        Initialize the repository with a DynamoDB table name.
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(TABLE_NAME)

    def save_pagination_state(self, pagination_state: dict[str, Optional[str]]) -> None:
        """
        Save the pagination state in the DynamoDB table.

        :param state: Dictionary containing the pagination state
        """
        try:
            self.table.put_item(Item=pagination_state)
        except ClientError as e:
            logger.error("Error saving pagination state: %s", e)
            raise

    def get_pagination_state_by_user_id(self, user_id: str) -> dict[str, Optional[str]]:
        """
        Retrieve the pagination state for a given user ID from the DynamoDB table.

        :param user_id: User ID to retrieve the pagination state for
        :return: Dictionary containing the pagination state
        """
        try:
            response = self.table.get_item(Key={"user_id": user_id})
            return response.get("Item", {})
        except ClientError as e:
            logger.error("Error getting pagination state: %s", e)
            raise
