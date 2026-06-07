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
        logger.info("Received a valid prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    aws_request_id = getattr(context, "aws_request_id", None)
    logger.info("Full Event received: %s", json.dumps(event))
    logger.info("Request ID: %s", aws_request_id)

    try:
        path_params = event.get("pathParameters") or {}
        campaign_id = path_params.get("campaign_id")

        if not campaign_id:
            logger.warning("Request failed: Missing campaign_id in path")
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "missing campaign_id in path"}), 
            }

        body_str = event.get("body") or "{}"
        body = json.loads(body_str)

        if not body:
            logger.warning("Request failed: Empty request body")
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "missing request body"}), 
            }

        existing_campaign = campaign_repo.get_campaign_by_id(campaign_id)
        if not existing_campaign:
            logger.warning("Request failed: Campaign ID %s not found", campaign_id)
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
                    "body": json.dumps({"message": "invalid request body: end_time must be after start_time"}),
                }

            body["status"] = get_campaign_status(start_time_str, end_time_str)

        logger.info("Attempting to update campaign: %s", campaign_id)
        campaign_details = campaign_repo.update_campaign(campaign_id, body, existing_campaign)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*" 
            },
            "body": json.dumps(
                {
                    "message": "campaign updated successfully", 
                    **campaign_details,
                }
            ),
        }

    except json.JSONDecodeError:
        logger.error("JSONDecodeError: Invalid JSON format in body")
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "invalid JSON format"}), 
        }
    except ValueError as e:
        logger.error("ValueError encountered: %s", str(e))
        return {
            "statusCode": 400,
            "body": json.dumps({"message": str(e)}), 
        }
    except Exception as e:
        logger.error("Unexpected Exception: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "failed to update campaign", "error": str(e)}), 
        }
        