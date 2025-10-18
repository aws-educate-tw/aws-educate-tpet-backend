import logging
import os
import time
from typing import Any

import requests
from sqs import get_sqs_message, send_message_to_queue

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get environment variables
AUTO_RESUMER_SQS_QUEUE_URL = os.getenv("AUTO_RESUMER_SQS_QUEUE_URL")
UPSERT_RUN_SQS_QUEUE_URL = os.getenv("UPSERT_RUN_SQS_QUEUE_URL")
ENVIRONMENT = os.environ.get("ENVIRONMENT")
DOMAIN_NAME = os.getenv("DOMAIN_NAME")


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
            response.raise_for_status()
            health_check_api_response_json = response.json()

            if health_check_api_response_json.get("status") == "HEALTHY":
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
    aws_request_id: str,
) -> dict[str, Any]:
    """
    Process a single SQS message:
    1. Ensure Aurora database is awake
    2. Forward message to upsert_run queue
    3. Delete message from auto-resumer queue

    :param message: The parsed SQS message
    :param aws_request_id: AWS request ID for tracking
    :param target_sqs_url: The target SQS queue URL to forward the message to
    :return: Response with status code and body
    """
    logger.info("Attempting to wake up Aurora database. Request ID: %s", aws_request_id)

    if not ensure_database_awake():
        raise RuntimeError("Aurora DB unavailable")

    # Aurora is awake, forward message to upsert_run SQS queue
    logger.info(
        "Aurora database is awake, forwarding message to upsert_run SQS queue. Request ID: %s",
        aws_request_id,
    )

    if not forward_message_to_target_queue(message, UPSERT_RUN_SQS_QUEUE_URL):
        raise RuntimeError("Failed to forward message to upsert_run queue")


def lambda_handler(event: dict[str, Any], context) -> dict[str, Any]:
    """
    Lambda handler for auto-resumer SQS.
    Triggered by auto-resumer SQS, ensures Aurora database is awake,
    then forwards messages to upsert_run SQS queue.

    :param event: The event from SQS trigger
    :param context: Lambda context
    :return: Response with batch item failures if any
    """
    logger.info("Lambda triggered with event: %s", event)

    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    batch_item_failures = []

    for record in event["Records"]:
        sqs_message = None
        try:
            sqs_message = get_sqs_message(record)
        except Exception as e:
            logger.error("Error getting SQS message: %s", e)
            batch_item_failures.append({"itemIdentifier": record["messageId"]})
            continue

        try:
            process_sqs_message(
                sqs_message,
                context.aws_request_id,
            )

        except Exception as e:
            logger.error("Error processing message: %s", e)
            batch_item_failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": batch_item_failures}
