import logging
import os

import boto3
from boto3.dynamodb.conditions import Key
from time_util import get_current_utc_time

logger = logging.getLogger(__name__)
logger.setLevel("INFO")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

COHORT = os.getenv("COHORT_NAME")


def get_campaign_by_id(campaign_id: str) -> dict:
    try:
        response = table.query(
            KeyConditionExpression=Key("cohort").eq(COHORT) & Key("campaign_id_created_at").begins_with(campaign_id)
        )
        items = response.get("Items", [])
        return items[0] if items else None
    except Exception as e:
        logger.error("Error querying campaign: %s", str(e))
        raise e


def update_campaign(campaign_id: str, update_data: dict) -> dict:
    existing_item = get_campaign_by_id(campaign_id)
    if not existing_item:
        return None

    pk = existing_item["cohort"]
    sk = existing_item["campaign_id_created_at"]

    field_mapping = {
        "campaign_name": "campaign_name",
        "campaign_start_time": "start_date",
        "campaign_end_time": "end_date",
        "campaign_location": "locations", 
        "is_active": "is_active",
        "status": "status"
    }

    update_expression = "SET updated_at = :val_now"
    expression_attribute_values = {":val_now": get_current_utc_time()}
    expression_attribute_names = {}

    for api_key, db_key in field_mapping.items():
        if api_key in update_data:
            attr_name = f"#{api_key}"
            attr_val = f":{api_key}"
            
            update_expression += f", {attr_name} = {attr_val}"
            expression_attribute_names[attr_name] = db_key
            expression_attribute_values[attr_val] = update_data[api_key]

    try:

        response = table.update_item(
            Key={
                "cohort": pk,
                "campaign_id_created_at": sk
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="ALL_NEW"
        )

        updated_item = response.get("Attributes", {})
        logger.info("Campaign %s updated successfully", campaign_id)
        
        return {
            "message": "campaign updated successfully",
            "campaign_id": campaign_id,
            "campaign_name": updated_item.get("campaign_name"),
            "campaign_start_time": updated_item.get("start_date"),
            "campaign_end_time": updated_item.get("end_date"),
            "campaign_location": updated_item.get("locations"),
            "campaign_created_at": updated_item.get("created_at"),
            "updated_at": updated_item.get("updated_at"),
            "is_active": updated_item.get("is_active", True)
        }

    except Exception as e:
        logger.error("Failed to update campaign: %s", str(e))
        raise e