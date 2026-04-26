import json
import logging

from botocore.exceptions import ClientError
from campaign_run_repository import CampaignRunRepository

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

campaign_run_repo = CampaignRunRepository()

REQUIRED_FIELDS = ["registration_deadline", "max_participants"]


def lambda_handler(event: dict, context: object) -> dict:
    """Lambda handler for PUT /rsvp-service/internal/campaign-runs/{campaign_id_run_id}."""

    aws_request_id = getattr(context, "aws_request_id", None)
    logger.info("Received event: %s", event)

    if event.get("action") == "PREWARM":
        logger.info(
            "Received a prewarm request. Skipping business logic. Request ID: %s",
            aws_request_id,
        )
        return {"statusCode": 200, "body": "Successfully warmed up"}

    # Parse composite path param: "{campaign_id}_{run_id}"
    # campaign_id = "evt_" (4 chars) + uuid4().hex (32 chars) = 36 chars total.
    # Split by index rather than split("_") because campaign_id contains "_".
    CAMPAIGN_ID_LEN = 36
    raw_path_param = (event.get("pathParameters") or {}).get("campaign_id_run_id", "")
    if (
        len(raw_path_param) <= CAMPAIGN_ID_LEN + 1
        or not raw_path_param.startswith("evt_")
        or raw_path_param[CAMPAIGN_ID_LEN] != "_"
    ):
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "Path parameter must be in the format '{campaign_id}_{run_id}'.",
                    "error": "MISSING_FIELDS",
                    "request_id": aws_request_id,
                }
            ),
        }
    campaign_id = raw_path_param[:CAMPAIGN_ID_LEN]
    run_id = raw_path_param[CAMPAIGN_ID_LEN + 1 :]

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

    # Validate required body fields
    missing = [f for f in REQUIRED_FIELDS if not body.get(f)]
    if missing:
        logger.error(
            "Missing required fields: %s. Request ID: %s", missing, aws_request_id
        )
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": f"Missing required fields: {', '.join(missing)}.",
                    "error": "MISSING_FIELDS",
                    "request_id": aws_request_id,
                }
            ),
        }

    config = {
        "registration_deadline": body["registration_deadline"],
        "max_participants": body["max_participants"],
        "is_active": body.get("is_active", True),
    }

    try:
        campaign_run_repo.upsert_run_configuration(campaign_id, run_id, config)
    except ClientError as e:
        logger.error(
            "Database error upserting run configuration: %s. Request ID: %s",
            e,
            aws_request_id,
        )
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "Failed to upsert run configuration.",
                    "error": "DB_ERROR",
                    "request_id": aws_request_id,
                }
            ),
        }

    logger.info(
        "Successfully upserted run configuration for campaign_id=%s run_id=%s. Request ID: %s",
        campaign_id,
        run_id,
        aws_request_id,
    )

    # Build response data with the upserted configuration
    response_data = {
        "campaign_id": campaign_id,
        "run_id": run_id,
        "registration_deadline": config["registration_deadline"],
        "max_participants": config["max_participants"],
        "is_active": config["is_active"],
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "status": "SUCCESS",
                "data": response_data,
            }
        ),
    }
