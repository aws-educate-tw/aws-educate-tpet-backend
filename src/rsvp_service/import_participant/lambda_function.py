import json
import logging
import uuid
from datetime import UTC, datetime

from botocore.exceptions import ClientError
from participants_repository import ParticipantsRepository

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

participants_repo = ParticipantsRepository()

REQUIRED_FIELDS = ["email", "campaign_id", "name"]


def lambda_handler(event: dict, context: object) -> dict:
    """Lambda handler for POST /rsvp-service/internal/runs/{run_id}/participants/."""

    aws_request_id = getattr(context, "aws_request_id", None)
    logger.info("Received event: %s", event)

    if event.get("action") == "PREWARM":
        logger.info(
            "Received a prewarm request. Skipping business logic. Request ID: %s",
            aws_request_id,
        )
        return {"statusCode": 200, "body": "Successfully warmed up"}

    # run_id comes from the path parameter
    run_id = (event.get("pathParameters") or {}).get("run_id")
    if not run_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "'run_id' path parameter is required.",
                    "error": "MISSING_FIELDS",
                    "request_id": aws_request_id,
                }
            ),
        }

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

    email = body["email"]
    campaign_id = body["campaign_id"]
    name = body["name"]
    campaign_participant_uniq_handle = f"{campaign_id}#{email}"

    # Step 1 & 2: Check GSI — reuse participant_id if this email already
    # exists under this campaign in a previous run, otherwise generate a new one.
    try:
        existing_participant_id = participants_repo.find_existing_participant_id(
            campaign_participant_uniq_handle
        )
    except ClientError as e:
        logger.error(
            "Database error querying existing participant: %s. Request ID: %s",
            e,
            aws_request_id,
        )
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "Failed to import participant.",
                    "error": "DB_ERROR",
                    "request_id": aws_request_id,
                }
            ),
        }

    participant_id = existing_participant_id or str(uuid.uuid4())
    if existing_participant_id:
        logger.info(
            "Reusing existing participant_id=%s for handle=%s",
            participant_id,
            campaign_participant_uniq_handle,
        )
    else:
        logger.info(
            "Generated new participant_id=%s for handle=%s",
            participant_id,
            campaign_participant_uniq_handle,
        )

    # Step 3: Build item
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    item = {
        "run_id": run_id,
        "participant_id": participant_id,
        "email": email,
        "campaign_id": campaign_id,
        "name": name,
        "campaign_participant_uniq_handle": campaign_participant_uniq_handle,
        "rsvp_status": "PENDING",
        "created_at": now,
        "updated_at": now,
    }

    # Step 4: Write to DynamoDB
    try:
        participants_repo.put_participant(item)
    except ClientError as e:
        logger.error(
            "Database error writing participant: %s. Request ID: %s",
            e,
            aws_request_id,
        )
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "Failed to import participant.",
                    "error": "DB_ERROR",
                    "request_id": aws_request_id,
                }
            ),
        }

    logger.info(
        "Successfully imported participant_id=%s for run_id=%s. Request ID: %s",
        participant_id,
        run_id,
        aws_request_id,
    )
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "status": "SUCCESS",
                "data": {"participant_id": participant_id},
            }
        ),
    }
