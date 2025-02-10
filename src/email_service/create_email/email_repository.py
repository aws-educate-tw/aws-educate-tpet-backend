import logging
import os

import boto3
import time_util
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLE_NAME = os.getenv("EMAIL_DYNAMODB_TABLE")


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
        last_evaluated_key: dict[str, str] | None,
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
        last_evaluated_key: dict[str, str] | None,
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
                "IndexName": "email-run_id-status-gsi",
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

    def query_emails_by_run_id_and_created_at_gsi(
        self,
        run_id: str,
        limit: int,
        last_evaluated_key: dict[str, str] | None,
        sort_order: str,
    ) -> dict[str, str]:
        """
        Query emails from the DynamoDB table based on run_id, created_at, and pagination parameters.

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
                "IndexName": "email-run_id-created_at-gsi",
                "KeyConditionExpression": Key("run_id").eq(run_id),
            }

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.table.query(**query_kwargs)
            return response
        except ClientError as e:
            logger.error("Error querying emails by created_at: %s", e)
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

    def get_email_by_id(self, run_id: str, email_id: str) -> dict[str, str] | None:
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

    def save_email(self, email: dict[str, str]) -> str | None:
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
        Update the status of an email record in the DynamoDB table.

        Parameters:
            run_id (str): The unique identifier representing the run.
            email_id (str): The unique identifier for the email.
            status (str): The new status to be set for the email record.

        Raises:
            KeyError: If the record with the specified run_id and email_id does not exist.
            ClientError: For any other error encountered during the update operation.

        This method updates the email record by setting:
            - The "status" field to the provided status value.
            - The "sent_at" field to the current UTC time.
            - The "updated_at" field to the current UTC time.
        It ensures that the item exists before the update operation via a condition expression.
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
                ConditionExpression="attribute_exists(run_id) AND attribute_exists(email_id)",  # Ensure item exists
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.error("Item not found: run_id=%s, email_id=%s", run_id, email_id)
                raise KeyError(
                    f"Item with run_id={run_id} and email_id={email_id} not found"
                ) from e
            else:
                logger.error("Error updating email status: %s", e)
                raise
