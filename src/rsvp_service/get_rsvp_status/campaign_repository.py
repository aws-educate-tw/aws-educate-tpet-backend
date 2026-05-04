import logging

import boto3
import os  
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()


class CampaignRepository:
    def __init__(self): 
        self.dynamodb = boto3.resource("dynamodb")
        table_name = os.environ.get("CAMPAIGN_TABLE")
        if not table_name:
            logger.error("CAMPAIGN_TABLE environment variable is not set")
            raise ValueError("CAMPAIGN_TABLE not set")
            
        self.table = self.dynamodb.Table(table_name)

    def get_campaign_by_id(self, campaign_id, cohort="8"):
        try:
            response = self.table.query(
                KeyConditionExpression=Key("cohort").eq(cohort)
                & Key("campaign_id_created_at").begins_with(campaign_id)
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except Exception as e:
            logger.error("Error querying campaign in campaign_repository: %s", e)
            raise e
