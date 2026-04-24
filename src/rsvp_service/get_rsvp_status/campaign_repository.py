import boto3
import logging
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger()

class CampaignRepository:
    def __init__(self, table_name):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)

    def get_run(self, campaign_id, run_id):
        try:
            response = self.table.get_item(Key={
                'campaign_id': campaign_id,
                'run_id': run_id
            })
            return response.get('Item')
        except Exception as e:
            logger.error(f"Error fetching run: {str(e)}")
            raise e

    def scan_run_by_id(self, run_id):
        try:
            response = self.table.scan(FilterExpression=Attr('run_id').eq(run_id))
            items = response.get('Items', [])
            return items[0] if items else None
        except Exception as e:
            logger.error(f"Error scanning run: {str(e)}")
            raise e