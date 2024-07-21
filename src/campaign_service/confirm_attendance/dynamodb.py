import logging

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DynamoDB:
    """
    DynamoDB operations
    """
    def __init__(self):
        self.dynamodb_client = boto3.resource(
            'dynamodb'
        )

    def put_item(self, table_name: str, item: dict):
        try:
            table = self.dynamodb_client.Table(table_name)
            table.put_item(Item=item)
            logger.info("Saved email record to DynamoDB: %s", item.get("email_id"))
        except Exception as e:
            logger.error("Error saving email record to DynamoDB: %s", e)
            raise