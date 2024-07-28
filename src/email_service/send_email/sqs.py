import json
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")


def delete_sqs_message(sqs_client, queue_url, receipt_handle):
    try:
        sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        logger.info("Deleted message from SQS: %s", receipt_handle)
    except Exception as e:
        logger.error("Error deleting message from SQS: %s", e)
        raise


def get_sqs_message(record):
    body = json.loads(record["body"])
    receipt_handle = record["receiptHandle"]
    logger.info("Processing message with run_id: %s", body.get("run_id"))

    # Add receipt_handle to the body and return it
    body["receipt_handle"] = receipt_handle

    return body
