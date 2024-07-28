import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class SQS:
    """
    SQS operations
    """
    def __init__(self):
        self.sqs_client = boto3.client(
            'sqs'
        )

    def delete_message(self, queue_url: str, receipt_handle: str):
        try:
            self.sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.info("Deleted message from SQS: %s", receipt_handle)
        except Exception as e:
            logger.error("Error deleting message from SQS: %s", e)
            raise