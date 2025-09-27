import json
import logging
import os
import time
from typing import Any

import requests
from sqs import delete_sqs_message, get_sqs_message, send_message_to_queue

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get environment variables
AUTO_RESUMER_SQS_QUEUE_URL = os.getenv("AUTO_RESUMER_SQS_QUEUE_URL")
CREATE_EMAIL_SQS_QUEUE_URL = os.getenv("CREATE_EMAIL_SQS_QUEUE_URL")
UPSERT_RUN_SQS_QUEUE_URL = os.getenv("UPSERT_RUN_SQS_QUEUE_URL")
BUCKET_NAME = os.getenv("BUCKET_NAME")
ENVIRONMENT = os.environ.get("ENVIRONMENT")
DOMAIN_NAME = os.getenv("DOMAIN_NAME")


class ErrorResponder:
    """A helper class to create standardized error responses with a request ID."""

    def __init__(self, request_id: str):
        self._request_id = request_id

    def create_error_response(self, status_code: int, message: str) -> dict[str, Any]:
        """Creates a standardized error response."""
        error_body = {
            "message": f"{message}, Request ID: {self._request_id}",
            "request_id": self._request_id,
        }
        return {
            "statusCode": status_code,
            "body": json.dumps(error_body),
            "headers": {"Content-Type": "application/json"},
        }


def ensure_database_awake() -> bool:
    """
    Call health check API to ensure Aurora Serverless v2 is awake.

    :return: True if database is confirmed awake, False otherwise
    """
    health_check_url = f"https://{ENVIRONMENT}-email-service-internal-api-tpet.{DOMAIN_NAME}/{ENVIRONMENT}/email-service/health"
    max_retries = 10
    retry_delay = 7  # seconds

    for attempt in range(max_retries):
        try:
            logger.info(
                "Attempting database health check (attempt %d/%d)",
                attempt + 1,
                max_retries,
            )
            response = requests.get(health_check_url, timeout=5)

            if response.status_code == 200:
                logger.info("Database confirmed to be awake and healthy")
                return True
            else:
                logger.warning(
                    "Health check failed with status code: %d", response.status_code
                )

            # If we haven't returned yet, we need to retry
            if attempt < max_retries - 1:
                logger.info("Waiting %d seconds before retrying...", retry_delay)
                time.sleep(retry_delay)

        except Exception as e:
            logger.error("Error during database health check: %s", str(e))
            if attempt < max_retries - 1:
                logger.info("Waiting %d seconds before retrying...", retry_delay)
                time.sleep(retry_delay)

    logger.error("Database health check failed after maximum retries")
    return False


def forward_message_to_target_queue(
    message: dict[str, Any], target_queue_url: str
) -> bool:
    """
    Forward a message from auto-resumer queue to a target queue.

    :param message: The SQS message to forward
    :return: True if message was forwarded successfully, False otherwise
    """
    try:
        logger.info("Forwarding message to target SQS queue")
        send_message_to_queue(target_queue_url, message)
        logger.info("Successfully forwarded message to target SQS queue")
        return True
    except Exception as e:
        logger.error("Failed to forward message to target SQS queue: %s", str(e))
        return False


def process_sqs_message(
    message: dict[str, Any],
    receipt_handle: str,
    aws_request_id: str,
    error_responder: ErrorResponder,
) -> dict[str, Any]:
    """
    Process a single SQS message:
    1. Ensure Aurora database is awake
    2. Forward message to upsert_run queue
    3. Delete message from auto-resumer queue

    :param message: The parsed SQS message
    :param receipt_handle: The receipt handle for the SQS message
    :param aws_request_id: AWS request ID for tracking
    :param target_sqs_url: The target SQS queue URL to forward the message to
    :return: Response with status code and body
    """
    try:
        # Try to wake up Aurora database
        logger.info(
            "Attempting to wake up Aurora database. Request ID: %s", aws_request_id
        )

        if not ensure_database_awake():
            logger.error(
                "Failed to wake up Aurora database after maximum retries. Request ID: %s",
                aws_request_id,
            )
            # Don't delete the message, it will be retried automatically by SQS
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "message": "Failed to wake up Aurora database",
                        "error": "Database connection error",
                        "request_id": aws_request_id,
                    }
                ),
            }

        # Aurora is awake, forward message to upsert_run SQS queue
        logger.info(
            "Aurora database is awake, forwarding message to upsert_run SQS queue. Request ID: %s",
            aws_request_id,
        )

        # Forward the message to upsert_run SQS queue
        success_upsert = forward_message_to_target_queue(
            message, UPSERT_RUN_SQS_QUEUE_URL
        )
        if not success_upsert:
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "message": "Failed to forward message to upsert_run SQS queue",
                        "error": "Message forwarding error",
                        "request_id": aws_request_id,
                    }
                ),
            }
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Message processed successfully",
                    "request_id": aws_request_id,
                }
            ),
        }
    except Exception as e:
        logger.error(
            "Error processing message: %s. Request ID: %s", str(e), aws_request_id
        )
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "message": f"An unexpected error occurred: {e}",
                    "error": "Server error",
                    "request_id": aws_request_id,
                }
            ),
        }


def lambda_handler(event: dict[str, Any], context) -> dict[str, Any]:
    """
    Lambda handler for auto-resumer SQS.
    Triggered by auto-resumer SQS, ensures Aurora database is awake,
    then forwards messages to upsert_run SQS queue.

    :param event: The event from SQS trigger
    :param context: Lambda context
    :return: Response with status code and body
    """
    logger.info("Lambda triggered with event: %s", event)
    error_responder = ErrorResponder(context.aws_request_id)

    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    for record in event["Records"]:
        sqs_message = None
        try:
            sqs_message = get_sqs_message(record)
        except Exception as e:
            logger.error("Error getting SQS message: %s", e)
            continue

        try:
            process_sqs_message(
                sqs_message,
                record.get("receiptHandle"),
                context.aws_request_id,
                error_responder,
            )

        except Exception as e:
            logger.error("Error processing message: %s", e)
            raise
        finally:
            if sqs_message and AUTO_RESUMER_SQS_QUEUE_URL:
                try:
                    delete_sqs_message(
                        AUTO_RESUMER_SQS_QUEUE_URL,
                        sqs_message["receipt_handle"],
                    )
                    logger.info(
                        "Deleted message from SQS: %s", sqs_message["receipt_handle"]
                    )
                except Exception as e:
                    logger.error("Error deleting SQS message: %s", e)
            elif not AUTO_RESUMER_SQS_QUEUE_URL:
                logger.error(
                    "AUTO_RESUMER_SQS_QUEUE_URL is not available: %s",
                    AUTO_RESUMER_SQS_QUEUE_URL,
                )
