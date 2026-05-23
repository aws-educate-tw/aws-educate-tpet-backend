import json
import logging

from campaign_repository import CampaignRepository
from time_util import get_current_utc_time, parse_iso8601_to_datetime
from campaign_status_enum import CampaignStatus

logger = logging.getLogger(__name__)
logger.setLevel("INFO")
campaign_repo = CampaignRepository()

def get_campaign_status(start_date: str, end_date: str) -> str:
    start_time = parse_iso8601_to_datetime(start_date)
    end_time = parse_iso8601_to_datetime(end_date)
    current_time = parse_iso8601_to_datetime(get_current_utc_time())

    if current_time < start_time:
        return CampaignStatus.UPCOMING.value
    elif current_time <= end_time:
        return CampaignStatus.ACTIVE.value
    else:
        return CampaignStatus.COMPLETED.value
    
def lambda_handler(event, context):

    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    aws_request_id = getattr(context, "aws_request_id", None)
    logger.info("Received event: %s. Request ID: %s", event, aws_request_id)

    try:
        campaign_id = event.get("pathParameters", {}).get("campaign_id")
        if not campaign_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "missing campaign_id"}), 
            }

        body = json.loads(event.get("body", "{}"))

        if not body:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "missing campaign_id"}), 
            }

        existing_campaign = campaign_repo.get_campaign_by_id(campaign_id)
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

        campaign_details = campaign_repo.update_campaign(campaign_id, body, existing_campaign)

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