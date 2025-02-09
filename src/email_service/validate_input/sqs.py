import json
import logging
from decimal import Decimal

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize SQS client
sqs_client = boto3.client("sqs")


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def send_message_to_queue(queue_url: str, message: dict) -> dict:
    """
    Send a message to an SQS queue.

    :param queue_url: The URL of the queue to send to
    :param message: The message to send
    :return: The response from SQS
    """
    try:
        response = sqs_client.send_message(
            QueueUrl=queue_url, MessageBody=json.dumps(message, default=decimal_default)
        )
        logger.info(
            "Successfully sent message to queue: %s, MessageId: %s",
            queue_url,
            response["MessageId"],
        )
        return response
    except Exception as e:
        logger.error("Failed to send message to queue %s: %s", queue_url, str(e))
        raise
