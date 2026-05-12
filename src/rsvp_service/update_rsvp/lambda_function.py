import json
import logging
from datetime import UTC, datetime

from botocore.exceptions import ClientError
from campaign_run_repository import CampaignRunRepository
from jwt_util import AuthenticationError, decode_rsvp_token
from participant_repository import ParticipantRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ALLOWED_ACTIONS = {"ATTEND", "NOT_ATTEND"}

participant_repository = ParticipantRepository()
campaign_run_repository = CampaignRunRepository()


def _iso_utc_now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def lambda_handler(event, context):
    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}
    
    aws_request_id = getattr(context, "aws_request_id", None)
    logger.info("Received event: %s. Request ID: %s", event, aws_request_id)

    try:
        path_params = event.get("pathParameters", {})
        raw_id = path_params.get("run_id_participant_id", "")

        if "_" not in raw_id:
            return build_response(
                400, {"code": "INVALID_PATH_FORMAT", "message": "Invalid ID format"}
            )

        path_run_id, path_participant_id = raw_id.rsplit("_", 1)
        token_payload = decode_rsvp_token(event.get("headers"))

        run_id = token_payload.get("run_id")
        participant_id = token_payload.get("participant_id")
        campaign_id = token_payload.get("campaign_id")
        email_id = token_payload.get("email_id")
        if not run_id or not participant_id or not campaign_id or not email_id:
            raise AuthenticationError("Token payload is incomplete")

        if run_id != path_run_id or participant_id != path_participant_id:
            raise AuthenticationError("Token does not match requested participant")

        run_item = campaign_run_repository.get_run(campaign_id, run_id)
        if not run_item:
            return build_response(
                500, {"code": "INTERNAL_ERROR", "message": "Internal server error"}
            )

        deadline = run_item.get("registration_deadline")
        if deadline and _iso_utc_now() > deadline:
            return build_response(
                403,
                {
                    "code": "REGISTRATION_CLOSED",
                    "message": "Registration is closed",
                },
            )

        try:
            body = json.loads(event.get("body", "{}"))
        except json.JSONDecodeError:
            return build_response(
                400,
                {"code": "INVALID_REQUEST", "message": "Invalid JSON request body"},
            )

        new_status = body.get("action")
        if new_status not in ALLOWED_ACTIONS:
            return build_response(
                400,
                {
                    "code": "INVALID_ACTION",
                    "message": "action must be ATTEND or NOT_ATTEND",
                },
            )

        transact_items = [
            {
                "Update": {
                    "TableName": participant_repository.table_name,
                    "Key": {
                        "run_id": {"S": run_id},
                        "participant_id": {"S": participant_id},
                    },
                    "UpdateExpression": "SET #r = :r, updated_at = :u",
                    "ExpressionAttributeNames": {"#r": "rsvp_status"},
                    "ExpressionAttributeValues": {
                        ":r": {"S": new_status},
                        ":u": {"S": _iso_utc_now()},
                    },
                    "ConditionExpression": "attribute_exists(run_id) AND attribute_exists(participant_id)",
                }
            }
        ]

        participant_repository.update_rsvp_transaction(transact_items)

        return build_response(
            200, {"status": "SUCCESS", "data": {"currentStatus": new_status}}
        )

    except AuthenticationError as e:
        logger.warning("Authentication failed: %s", e)
        return build_response(401, {"code": "INVALID_TOKEN", "message": str(e)})
    except ClientError as e:
        logger.error("DynamoDB error: %s", e)
        return build_response(
            500, {"code": "INTERNAL_ERROR", "message": "Internal server error"}
        )
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return build_response(
            500, {"code": "INTERNAL_ERROR", "message": "Internal server error"}
        )


def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }
