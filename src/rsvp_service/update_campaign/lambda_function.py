import json
import logging

from campaign_repository import get_campaign_by_id, update_campaign
from time_util import get_current_utc_time, parse_iso8601_to_datetime

logger = logging.getLogger(__name__)
logger.setLevel("INFO")

def get_campaign_status(start_date: str, end_date: str) -> str:
    start_time = parse_iso8601_to_datetime(start_date)
    end_time = parse_iso8601_to_datetime(end_date)
    current_time = parse_iso8601_to_datetime(get_current_utc_time())

    if current_time < start_time:
        return "UPCOMING"
    elif current_time <= end_time:
        return "ACTIVE"
    else:
        return "COMPLETED"

def lambda_handler(event, context):
    try:
        campaign_id = event.get("pathParameters", {}).get("campaign_id")
        if not campaign_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "invalid request body"}), 
            }

        body = json.loads(event.get("body", "{}"))

        if not body:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "invalid request body"}), 
            }

        existing_campaign = get_campaign_by_id(campaign_id)
        if not existing_campaign:
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "campaign not found"}), 
            }

        start_time_str = body.get("campaign_start_time") or existing_campaign.get("start_date")
        end_time_str = body.get("campaign_end_time") or existing_campaign.get("end_date")

        if "campaign_start_time" in body or "campaign_end_time" in body:
            start_dt = parse_iso8601_to_datetime(start_time_str)
            end_dt = parse_iso8601_to_datetime(end_time_str)

            if end_dt <= start_dt:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"message": "invalid request body"}),
                }

            body["status"] = get_campaign_status(start_time_str, end_time_str)

        campaign_details = update_campaign(campaign_id, body)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "campaign updated successfully", 
                    **campaign_details,
                }
            ),
        }

    except json.JSONDecodeError:
        logger.error("JSONDecodeError: Invalid JSON format")
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "invalid request body"}), 
        }
    except ValueError as e:
        logger.error("ValueError: %s", str(e))
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "invalid request body"}), 
        }
    except Exception as e:
        logger.error("Exception: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "failed to update campaign"}), 
        }