import logging
import os

import boto3
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SES:
    """
    SES operations
    """
    def __init__(self):
        self.ses_client = boto3.client(
            'ses',
            region_name='ap-northeast-1'
        )

    def send_email(self, formatted_source_email: str, receiver_email: str, email_title: str, formatted_content: str):
        try:
            response = self.ses_client.send_email(
                Source=formatted_source_email,
                Destination={"ToAddresses": [receiver_email]},
                Message={
                    "Subject": {"Data": email_title},
                    "Body": {"Html": {"Data": formatted_content}},
                },
            )
            return response
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            raise