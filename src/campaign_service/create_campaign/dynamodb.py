import json
import logging
import uuid

import boto3
from time_util import get_current_utc_time

logger = logging.getLogger()
logger.setLevel("INFO")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("campaign")


def create_campaign(body: dict) -> dict:
    """
    Create a new campaign in DynamoDB.

    :param body: The request body containing campaign details including status.
    :return: A dictionary with the campaign details.
    """
    campaign_id = uuid.uuid4().hex
    campaign_name = body["campaign_name"]
    description = body["description"]
    start_date = body["start_date"]
    end_date = body["end_date"]
    participant_limit = body["participant_limit"]
    locations = body["locations"]
    status = body["status"]

    now = get_current_utc_time()

    item = {
        "campaign_id": campaign_id,
        "start_date": start_date,
        "end_date": end_date,
        "participant_limit": participant_limit,
        "campaign_name": campaign_name,
        "description": description,
        "locations": json.dumps(locations),
        "created_at": now,
        "updated_at": now,
        "status": status,
    }

    table.put_item(Item=item)
    logger.info("Campaign created successfully with ID: %s", campaign_id)

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "description": description,
        "start_date": start_date,
        "end_date": end_date,
        "participant_limit": participant_limit,
        "locations": locations,
        "created_at": now,
        "updated_at": now,
        "status": status,
    }
