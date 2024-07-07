import logging
import os

import boto3
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SQS:
    """
    SQS operations
    """
    def __init__(self):
        self.sqs_client = boto3.client(
            'sqs',
            region_name=os.getenv('REGION_NAME')
        )

    def delete_message(self, queue_url: str, receipt_handle: str):
        try:
            self.sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.info("Deleted message from SQS: %s", receipt_handle)
        except Exception as e:
            logger.error(f"Error deleting message from SQS: {e}")
            raise