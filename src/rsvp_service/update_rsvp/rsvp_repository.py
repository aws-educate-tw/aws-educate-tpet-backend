import boto3
import os
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()

class RSVPRepository:
    def __init__(self):
        region = os.environ.get('AWS_REGION', 'us-west-2')
        self.dynamodb = boto3.client('dynamodb', region_name=region)
        self.table_name = os.environ.get('PARTICIPANT_TABLE', 'participant')

    def get_rsvp_record(self, run_id, participant_id):
        try:
            response = self.dynamodb.get_item(
                TableName=self.table_name,
                Key={
                    'run_id': {'S': run_id},
                    'participant_id': {'S': participant_id}
                }
            )
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error fetching record: {e}")
            raise

    def update_rsvp_transaction(self, transact_items):
        try:
            return self.dynamodb.transact_write_items(TransactItems=transact_items)
        except ClientError as e:
            logger.error(f"Transaction failed: {e}")
            raise