import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from campaign_repository import CampaignRepository
from campaign_run_repository import CampaignRunRepository
from jwt_util import AuthenticationError, decode_rsvp_token
from participant_repository import ParticipantRepository
from rsvp_status_enum import RsvpStatus

logger = logging.getLogger()
logger.setLevel(logging.INFO)

campaign_repository = CampaignRepository()
campaign_run_repository = CampaignRunRepository()
participant_repository = ParticipantRepository()


def _parse_iso_datetime(value):
    if not value:
        return None

    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def lambda_handler(event, context):
    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    aws_request_id = getattr(context, "aws_request_id", None)
    logger.info("Received event: %s. Request ID: %s", event, aws_request_id)

    try:
        path_params = event.get("pathParameters", {})
        run_id_participant_id = path_params.get("run_id_participant_id", "")
        parts = run_id_participant_id.rsplit("_", 1)
        if len(parts) < 2:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Invalid ID format"}),
            }
        path_run_id, path_participant_id = parts[0], parts[1]

        token_payload = decode_rsvp_token(event.get("headers"))
        run_id = token_payload.get("run_id")
        participant_id = token_payload.get("participant_id")
        campaign_id = token_payload.get("campaign_id")
        token_name = token_payload.get("name", "Unknown User")

        if not run_id or not participant_id or not campaign_id:
            raise AuthenticationError("Token payload is incomplete")

        if run_id != path_run_id or participant_id != path_participant_id:
            raise AuthenticationError("Token does not match requested participant")

        user_item = None
        run_item = None
        camp_master_item = None

        with ThreadPoolExecutor() as executor:
            future_participant = executor.submit(
                participant_repository.get_participant, run_id, participant_id
            )
            future_run = executor.submit(
                campaign_run_repository.get_run, campaign_id, run_id
            )
            future_camp = executor.submit(
                campaign_repository.get_campaign_by_id, campaign_id
            )

            user_item = future_participant.result()
            run_item = future_run.result()
            camp_master_item = future_camp.result()

        if not user_item or not run_item or not camp_master_item:
            logger.error(
                "Data missing - Participant: %s, Run: %s, Camp: %s",
                bool(user_item),
                bool(run_item),
                bool(camp_master_item),
            )
            return {
                "statusCode": 404,
                "body": json.dumps(
                    {"status": "error", "message": "Activity not found"}
                ),
            }

        now = datetime.now(UTC)
        deadline = run_item.get("registration_deadline")
        deadline_dt = _parse_iso_datetime(deadline)
        is_registration_closed = now > deadline_dt if deadline_dt else False

        response_data = {
            "status": "SUCCESS",
            "rsvp_status": user_item.get("rsvp_status", RsvpStatus.PENDING),
            "participant_name": user_item.get("name", token_name),
            "last_edited_time": user_item.get("updated_at"),
            "campaign_name": camp_master_item.get("campaign_name", ""),
            "campaign_start_time": camp_master_item.get("campaign_start_time", ""),
            "campaign_location": camp_master_item.get("campaign_location", ""),
            "registration_deadline": deadline,
            "is_registration_closed": is_registration_closed,
        }

        return {"statusCode": 200, "body": json.dumps(response_data)}

    except AuthenticationError as e:
        logger.warning("Authentication failed: %s", e)
        return {
            "statusCode": 401,
            "body": json.dumps({"code": "INVALID_TOKEN", "message": str(e)}),
        }
    except Exception as e:
        logger.error("System Error: %s", e)
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"code": "INTERNAL_ERROR", "message": "Internal server error"}
            ),
        }
