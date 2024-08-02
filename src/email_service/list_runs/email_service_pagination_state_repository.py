import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLE_NAME = "email_service_pagination_state"  # 確保這個表名是正確的


class EmailServicePaginationStateRepository:
    """Repository class for managing pagination state in DynamoDB for Email Service"""

    def __init__(self):
        """
        Initialize the repository with a DynamoDB table name.
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(TABLE_NAME)

    def save_pagination_state(self, pagination_state: dict[str, Optional[str]]) -> None:
        """
        Save the pagination state in the DynamoDB table.

        :param pagination_state: Dictionary containing the pagination state
        """
        try:
            self.table.put_item(Item=pagination_state)
        except ClientError as e:
            logger.error("Error saving pagination state: %s", e)
            raise

    def get_pagination_state_by_user_id_and_index_name(
        self, user_id: str, index_name: str
    ) -> dict[str, Optional[str]]:
        """
        Retrieve the pagination state for a given user ID and index name from the DynamoDB table.

        :param user_id: User ID to retrieve the pagination state for
        :param index_name: Index name to retrieve the pagination state for
        :return: Dictionary containing the pagination state
        """
        try:
            response = self.table.get_item(
                Key={"user_id": user_id, "index_name": index_name}
            )
            return response.get("Item", {})
        except ClientError as e:
            logger.error("Error getting pagination state: %s", e)
            raise
