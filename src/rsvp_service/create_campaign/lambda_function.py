import json
import logging
import uuid
from datetime import datetime, timezone

from botocore.exceptions import ClientError
from campaigns_repository import CampaignsRepository

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

campaigns_repo = CampaignsRepository()


def lambda_handler(event: dict, context: object) -> dict:
    """Lambda handler for POST /rsvp-service/campaigns — create a new campaign."""
    
    aws_request_id = getattr(context, "aws_request_id", None)
    logger.info("Received event: %s. Request ID: %s", event, aws_request_id)

    if event.get("action") == "PREWARM":
        logger.info(
            "Received a prewarm request. Skipping business logic. Request ID: %s", aws_request_id
        )
        return {"statusCode": 200, "body": "Successfully warmed up"}

    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError as e:
        logger.error(
            "Invalid JSON in request body: %s. Request ID: %s", e, aws_request_id
        )
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "Invalid JSON in request body.",
                    "error": "Invalid request format",
                    "request_id": aws_request_id,
                }
            ),
        }

    # Validate required field
    campaign_name = body.get("campaign_name")
    if not campaign_name:
        logger.error(
            "Missing required field 'campaign_name'. Request ID: %s", aws_request_id
        )
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "'campaign_name' is required and cannot be empty.",
                    "error": "MISSING_FIELDS",
                    "request_id": aws_request_id,
                }
            ),
        }
    
    cohort = body.get("cohort")
    if not cohort:
        logger.error("Missing required field 'cohort'. Request ID: %s", aws_request_id)
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "'cohort' is required and cannot be empty.",
                    "error": "INVALID_FIELDS",
                    "request_id": aws_request_id,
                }
            ),
        }

    campaign_id = f"evt_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    item = {
        "campaign_id": campaign_id,
        "cohort": cohort,
        "campaign_name": campaign_name,
        "campaign_start_time": body.get("campaign_start_time", ""),
        "campaign_end_time": body.get("campaign_end_time", ""),
        "campaign_location": body.get("campaign_location", ""),
        "created_at": now,
        "is_active": False,
    }

    try:
        campaigns_repo.create_campaign(item)
    except ClientError as e:
        logger.error(
            "Database error creating campaign: %s. Request ID: %s",
            e,
            aws_request_id,
        )
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "Failed to create campaign.",
                    "error": "DB_ERROR",
                    "request_id": aws_request_id,
                }
            ),
        }
    except Exception as e:
        logger.error(
            "Unexpected error: %s. Request ID: %s", e, aws_request_id
        )
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": f"An unexpected error occurred: {e}",
                    "error": "INTERNAL_ERROR",
                    "request_id": aws_request_id,
                }
            ),
        }

    logger.info(
        "Successfully created campaign with ID: %s. Request ID: %s",
        campaign_id,
        aws_request_id,
    )
    return {
        "statusCode": 201,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "status": "SUCCESS",
                "campaign_id": campaign_id,
                "created_at": now,
                "message": "Event created successfully.",
            }
        ),
    }
