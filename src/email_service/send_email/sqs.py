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


def process_sqs_message(record):
    body = json.loads(record["body"])
    receipt_handle = record["receiptHandle"]
    template_file_id = body.get("template_file_id")
    spreadsheet_id = body.get("spreadsheet_file_id")
    email_title = body.get("email_title")
    display_name = body.get("display_name")
    run_id = body.get("run_id")
    attachment_file_ids = body.get("attachment_file_ids", [])
    is_generate_certificate = body.get("is_generate_certificate", False)

    logger.info("Processing message with run_id: %s", run_id)

    return {
        "body": body,
        "receipt_handle": receipt_handle,
        "template_file_id": template_file_id,
        "spreadsheet_id": spreadsheet_id,
        "email_title": email_title,
        "display_name": display_name,
        "run_id": run_id,
        "attachment_file_ids": attachment_file_ids,
        "is_generate_certificate": is_generate_certificate,
    }
