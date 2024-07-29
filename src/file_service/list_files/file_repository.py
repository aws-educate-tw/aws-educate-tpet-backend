import logging
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLE_NAME = "file"


class FileRepository:
    """Repository class for managing files in DynamoDB"""

    def __init__(self):
        """
        Initialize the repository with a DynamoDB table name.
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(TABLE_NAME)

    def query_files_by_file_extension_and_created_at_gsi(
        self,
        file_extension: str,
        limit: int,
        last_evaluated_key: Optional[dict[str, str]],
        sort_order: str,
    ) -> dict[str, str]:
        """
        Query files from the DynamoDB table based on file extension and pagination parameters.

        :param file_extension: The file extension to filter by
        :param limit: The maximum number of items to return
        :param last_evaluated_key: The key to start with for pagination
        :param sort_order: The sort order, either 'ASC' or 'DESC'
        :return: The query response from DynamoDB
        """
        try:
            query_kwargs = {
                "Limit": limit,
                "ScanIndexForward": False if sort_order.upper() == "DESC" else True,
                "IndexName": "file_extension-created_at-gsi",
                "KeyConditionExpression": Key("file_extension").eq(file_extension),
            }

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.table.query(**query_kwargs)
            return response
        except ClientError as e:
            logger.error("Error querying files: %s", e)
            raise

    def get_file_by_id(self, file_id: str) -> Optional[dict[str, str]]:
        """
        Retrieve a file by its ID from the DynamoDB table.

        :param file_id: The ID of the file to retrieve
        :return: The file item, or None if not found
        """
        try:
            response = self.table.get_item(Key={"file_id": file_id})
            return response.get("Item")
        except ClientError as e:
            logger.error("Error getting file by ID: %s", e)
            return None

    def save_file(self, file: dict[str, str]) -> Optional[str]:
        """
        Save a file to the DynamoDB table.

        :param file: The file item to save
        :return: The ID of the saved file, or None if an error occurred
        """
        try:
            self.table.put_item(Item=file)
            return file["file_id"]
        except ClientError as e:
            logger.error("Error saving file: %s", e)
            return None

    def delete_file(self, file_id: str) -> None:
        """
        Delete a file by its ID from the DynamoDB table.

        :param file_id: The ID of the file to delete
        """
        try:
            self.table.delete_item(Key={"file_id": file_id})
        except ClientError as e:
            logger.error("Error deleting file: %s", e)

    def scan_files_by_file_extension(
        self, file_extension: str
    ) -> Optional[list[dict[str, str]]]:
        """
        Scan files from the DynamoDB table based on file extension.

        :param file_extension: The file extension to filter by
        :return: A list of files with the specified extension, or an empty list if an error occurred
        """
        try:
            response = self.table.scan(
                FilterExpression=Key("file_extension").eq(file_extension)
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error("Error scanning files by extension: %s", e)
            return []

    def query_files_by_created_year_and_created_at_gsi(
        self,
        created_year: int,
        limit: int,
        last_evaluated_key: Optional[dict[str, str]],
        sort_order: str,
    ) -> dict[str, str]:
        """
        Query files from the DynamoDB table based on created year and pagination parameters.

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
            logger.error("Error querying files by created year: %s", e)
            raise

    def query_files_by_created_year_month_and_created_at_gsi(
        self,
        created_year_month: str,
        limit: int,
        last_evaluated_key: Optional[dict[str, str]],
        sort_order: str,
    ) -> dict[str, str]:
        """
        Query files from the DynamoDB table based on created year and month and pagination parameters.

        :param created_year_month: The created year and month to filter by (format: 'YYYY-MM')
        :param limit: The maximum number of items to return
        :param last_evaluated_key: The key to start with for pagination
        :param sort_order: The sort order, either 'ASC' or 'DESC'
        :return: The query response from DynamoDB
        """
        try:
            query_kwargs = {
                "Limit": limit,
                "ScanIndexForward": False if sort_order.upper() == "DESC" else True,
                "IndexName": "created_year_month_created_at_gsi",
                "KeyConditionExpression": Key("created_year_month").eq(
                    created_year_month
                ),
            }

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.table.query(**query_kwargs)
            return response
        except ClientError as e:
            logger.error("Error querying files by created year and month: %s", e)
            raise

    def query_files_by_created_year_month_day_and_created_at_gsi(
        self,
        created_year_month_day: str,
        limit: int,
        last_evaluated_key: Optional[dict[str, str]],
        sort_order: str,
    ) -> dict[str, str]:
        """
        Query files from the DynamoDB table based on created year, month, and day and pagination parameters.

        :param created_year_month_day: The created year, month, and day to filter by (format: 'YYYY-MM-DD')
        :param limit: The maximum number of items to return
        :param last_evaluated_key: The key to start with for pagination
        :param sort_order: The sort order, either 'ASC' or 'DESC'
        :return: The query response from DynamoDB
        """
        try:
            query_kwargs = {
                "Limit": limit,
                "ScanIndexForward": False if sort_order.upper() == "DESC" else True,
                "IndexName": "created_year_month_day_created_at_gsi",
                "KeyConditionExpression": Key("created_year_month_day").eq(
                    created_year_month_day
                ),
            }

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.table.query(**query_kwargs)
            return response
        except ClientError as e:
            logger.error("Error querying files by created year, month, and day: %s", e)
            raise
