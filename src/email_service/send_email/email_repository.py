import logging
import os
from typing import Optional

import boto3
import time_util  # Import the time utility module
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLE_NAME = os.getenv("DYNAMODB_TABLE")


class EmailRepository:
    """Repository class for managing emails in DynamoDB"""

    def __init__(self):
        """
        Initialize the repository with a DynamoDB table name.
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(TABLE_NAME)

    def query_emails(
        self,
        run_id: str,
        limit: int,
        last_evaluated_key: Optional[dict[str, str]],
        sort_order: str,
    ) -> dict[str, str]:
        """
        Query emails from the DynamoDB table based on run_id and pagination parameters.

        :param run_id: The run ID to filter by
        :param limit: The maximum number of items to return
        :param last_evaluated_key: The key to start with for pagination
        :param sort_order: The sort order, either 'ASC' or 'DESC'
        :return: The query response from DynamoDB
        """
        try:
            query_kwargs = {
                "Limit": limit,
                "ScanIndexForward": False if sort_order.upper() == "DESC" else True,
                "KeyConditionExpression": Key("run_id").eq(run_id),
            }

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.table.query(**query_kwargs)
            return response
        except ClientError as e:
            logger.error("Error querying emails: %s", e)
            raise

    def query_emails_by_run_id_and_status_gsi(
        self,
        run_id: str,
        status: str,
        limit: int,
        last_evaluated_key: Optional[dict[str, str]],
        sort_order: str,
    ) -> dict[str, str]:
        """
        Query emails from the DynamoDB table based on run_id, status, and pagination parameters.

        :param run_id: The run ID to filter by
        :param status: The status to filter by
        :param limit: The maximum number of items to return
        :param last_evaluated_key: The key to start with for pagination
        :param sort_order: The sort order, either 'ASC' or 'DESC'
        :return: The query response from DynamoDB
        """
        try:
            query_kwargs = {
                "Limit": limit,
                "ScanIndexForward": False if sort_order.upper() == "DESC" else True,
                "IndexName": "run_id-status-gsi",
                "KeyConditionExpression": Key("run_id").eq(run_id)
                & Key("status").eq(status),
            }

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.table.query(**query_kwargs)
            return response
        except ClientError as e:
            logger.error("Error querying emails by status: %s", e)
            raise

    def query_all_emails_by_run_id_and_status_gsi(
        self,
        run_id: str,
        status: str,
        sort_order: str = "ASC",
    ) -> list[dict]:
        """
        Query all emails from the DynamoDB table based on run_id and status, using the run_id-status-gsi index, without pagination.

        :param run_id: The run ID to filter by
        :param status: The status to filter by
        :param sort_order: The sort order, either 'ASC' or 'DESC'
        :return: A list of all matching email items
        """
        all_emails = []
        last_evaluated_key = None

        while True:
            response = self.query_emails_by_run_id_and_status_gsi(
                run_id=run_id,
                status=status,
                limit=100,  # This limit is for each query call
                last_evaluated_key=last_evaluated_key,
                sort_order=sort_order,
            )
            all_emails.extend(response.get("Items", []))
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

        return all_emails

    def get_email_by_id(self, run_id: str, email_id: str) -> Optional[dict[str, str]]:
        """
        Retrieve an email by its run ID and email ID from the DynamoDB table.

        :param run_id: The run ID of the email to retrieve
        :param email_id: The email ID of the email to retrieve
        :return: The email item, or None if not found
        """
        try:
            response = self.table.get_item(Key={"run_id": run_id, "email_id": email_id})
            return response.get("Item")
        except ClientError as e:
            logger.error("Error getting email by ID: %s", e)
            return None

    def save_email(self, email: dict[str, str]) -> Optional[str]:
        """
        Save an email to the DynamoDB table.

        :param email: The email item to save
        :return: The ID of the saved email, or None if an error occurred
        """
        try:
            email["created_at"] = time_util.get_current_utc_time()
            self.table.put_item(Item=email)
            return email["email_id"]
        except ClientError as e:
            logger.error("Error saving email: %s", e)
            return None

    def delete_email(self, run_id: str, email_id: str) -> None:
        """
        Delete an email by its run ID and email ID from the DynamoDB table.

        :param run_id: The run ID of the email to delete
        :param email_id: The email ID of the email to delete
        """
        try:
            self.table.delete_item(Key={"run_id": run_id, "email_id": email_id})
        except ClientError as e:
            logger.error("Error deleting email: %s", e)

    def update_email_status(self, run_id: str, email_id: str, status: str) -> None:
        """
        Update the status, sent_at, and updated_at fields of an email in the DynamoDB table.

        :param run_id: The run ID of the email to update
        :param email_id: The email ID of the email to update
        :param status: The new status of the email
        """
        try:
            self.table.update_item(
                Key={"run_id": run_id, "email_id": email_id},
                UpdateExpression="SET #status = :status, sent_at = :sent_at, updated_at = :updated_at",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":status": status,
                    ":sent_at": time_util.get_current_utc_time(),
                    ":updated_at": time_util.get_current_utc_time(),
                },
            )
        except ClientError as e:
            logger.error("Error updating email status: %s", e)
            raise
