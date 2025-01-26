import logging

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

    def query_files(
        self,
        file_extension: str,
        limit: int,
        last_evaluated_key: dict[str, str] | None,
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

    def get_file_by_id(self, file_id: str) -> dict[str, str] | None:
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

    def save_file(self, file: dict[str, str]) -> str | None:
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

    def scan_files_by_file_extension(self, file_extension: str) -> list | None:
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
