import json
import logging

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize SQS client
sqs_client = boto3.client("sqs")


def delete_sqs_message(queue_url: str, receipt_handle: str) -> None:
    """
    Delete a message from an SQS queue.

    :param queue_url: The URL of the queue
    :param receipt_handle: The receipt handle of the message to delete
    """
    try:
        sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        logger.info("Deleted message from SQS: %s", receipt_handle)
    except Exception as e:
        logger.error("Error deleting message from SQS: %s", e)
        raise


def get_sqs_message(record: dict) -> dict:
    """
    Parse an SQS message from the record.

    :param record: The SQS message record
    :return: The parsed message body with receipt handle
    """
    body = json.loads(record["body"])
    receipt_handle = record["receiptHandle"]
    logger.info("Processing message with run_id: %s", body.get("run_id"))
    body["receipt_handle"] = receipt_handle
    return body


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
