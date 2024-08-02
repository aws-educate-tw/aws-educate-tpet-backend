import logging
import os
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLE_NAME = os.getenv("RUN_DYNAMODB_TABLE")


class RunRepository:
    """Repository class for managing runs in DynamoDB"""

    def __init__(self):
        """
        Initialize the repository with a DynamoDB table name.
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(TABLE_NAME)

    def query_runs_by_created_year_and_created_at_gsi(
        self,
        created_year: str,
        limit: int,
        last_evaluated_key: Optional[dict[str, str]],
        sort_order: str,
    ) -> dict[str, str]:
        """
        Query runs from the DynamoDB table based on created year and pagination parameters.

        :param created_year: The created year to filter by
        :param limit: The maximum number of items to return
        :param last_evaluated_key: The key to start with for pagination
        :param sort_order: The sort order, either 'ASC' or 'DESC'
        :return: The query response from DynamoDB
        """
        try:
            query_kwargs = {
                "Limit": limit,
                "ScanIndexForward": False if sort_order.upper() == "DESC" else True,
                "IndexName": "created_year_created_at_gsi",
                "KeyConditionExpression": Key("created_year").eq(created_year),
            }

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.table.query(**query_kwargs)
            return response
        except ClientError as e:
            logger.error("Error querying runs by created year: %s", e)
            raise

    def get_run_by_id(self, run_id: str) -> Optional[dict[str, str]]:
        """
        Retrieve a run by its ID from the DynamoDB table.

        :param run_id: The ID of the run to retrieve
        :return: The run item, or None if not found
        """
        try:
            response = self.table.get_item(Key={"run_id": run_id})
            return response.get("Item")
        except ClientError as e:
            logger.error("Error getting run by ID: %s", e)
            return None

    def save_run(self, run: dict[str, str]) -> Optional[str]:
        """
        Save a run to the DynamoDB table.

        :param run: The run item to save
        :return: The ID of the saved run, or None if an error occurred
        """
        try:
            self.table.put_item(Item=run)
            return run["run_id"]
        except ClientError as e:
            logger.error("Error saving run: %s", e)
            return None

    def delete_run(self, run_id: str) -> None:
        """
        Delete a run by its ID from the DynamoDB table.

        :param run_id: The ID of the run to delete
        """
        try:
            self.table.delete_item(Key={"run_id": run_id})
        except ClientError as e:
            logger.error("Error deleting run: %s", e)
