import logging
import os

import boto3
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DynamoDB:
    """
    DynamoDB operations
    """
    def __init__(self):
        self.dynamodb_client = boto3.resource(
            'dynamodb',
            region_name=os.getenv('REGION_NAME')
        )

    def put_item(self, table_name: str, item: dict):
        try:
            table = self.dynamodb_client.Table(table_name)
            table.put_item(Item=item)
            logger.info("Saved email record to DynamoDB: %s", item.get("email_id"))
        except Exception as e:
            logger.error(f"Error saving to DynamoDB: {e}")
            raise