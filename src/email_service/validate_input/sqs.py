import json
import logging

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize SQS client
sqs_client = boto3.client("sqs")


def send_message_to_queue(queue_url: str, message: dict) -> dict:
    """
    Send a message to an SQS queue.

    :param queue_url: The URL of the queue to send to
    :param message: The message to send
    :return: The response from SQS
    """
    try:
        response = sqs_client.send_message(
            QueueUrl=queue_url, MessageBody=json.dumps(message)
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
