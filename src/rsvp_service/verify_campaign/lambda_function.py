import json
import logging

from botocore.exceptions import ClientError
from campaigns_repository import CampaignsRepository

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

campaigns_repo = CampaignsRepository()


def lambda_handler(event: dict, context: object) -> dict:
    """Lambda handler for GET /rsvp-service/internal/campaign/{campaign_id}/check."""
    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    aws_request_id = getattr(context, "aws_request_id", None)
    logger.info("Received event: %s", event)

    campaign_id = (event.get("pathParameters") or {}).get("campaign_id")
    if not campaign_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "'campaign_id' path parameter is required.",
                    "error": "MISSING_FIELDS",
                    "request_id": aws_request_id,
                }
            ),
        }

    try:
        item = campaigns_repo.get_campaign_by_id(campaign_id)
    except ClientError as e:
        logger.error(
            "Database error fetching campaign %s: %s. Request ID: %s",
            campaign_id,
            e,
            aws_request_id,
        )
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "Failed to verify campaign.",
                    "error": "INTERNAL_ERROR",
                    "request_id": aws_request_id,
                }
            ),
        }

    if item is None:
        logger.warning(
            "Campaign not found: %s. Request ID: %s", campaign_id, aws_request_id
        )
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": f"Campaign '{campaign_id}' not found.",
                    "error": "Campaign_NOT_FOUND",
                    "request_id": aws_request_id,
                }
            ),
        }

    if not item.get("is_active", True):
        logger.warning(
            "Campaign is inactive: %s. Request ID: %s", campaign_id, aws_request_id
        )
        return {
            "statusCode": 403,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "Campaign is inactive.",
                    "error": "Campaign_INACTIVE",
                    "request_id": aws_request_id,
                }
            ),
        }

    logger.info(
        "Campaign verified successfully: %s. Request ID: %s",
        campaign_id,
        aws_request_id,
    )
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "status": "success",
                "data": {
                    "is_valid": True,
                    "campaign_id": item["campaign_id"],
                    "campaign_name": item.get("campaign_name", ""),
                    "is_active": item["is_active"],
                },
            }
        ),
    }
