import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from campaign_repository import CampaignRepository
from campaign_run_repository import CampaignRunRepository 
from participant_repository import ParticipantRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

campaign_repository = CampaignRepository(os.environ.get("CAMPAIGN_TABLE"))
campaign_run_repository = CampaignRunRepository(os.environ.get("CAMPAIGN_RUN_TABLE"))
participant_repository = ParticipantRepository(os.environ.get("PARTICIPANT_TABLE"))


def lambda_handler(event, context):
    try:
        path_params = event.get("pathParameters", {})
        run_id_participant_id = path_params.get("run_id_participant_id", "")
        parts = run_id_participant_id.rsplit("_", 1)
        if len(parts) < 2:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Invalid ID format"}),
            }
        run_id, participant_id = parts[0], parts[1]

        authorizer = (
            event.get("requestContext", {}).get("authorizer", {}).get("lambda", {})
        )
        campaign_id_from_token = authorizer.get("campaign_id")
        token_name = authorizer.get("name", "Unknown User")

        user_item = participant_repository.get_participant(run_id, participant_id)
        final_campaign_id = campaign_id_from_token or (
            user_item.get("campaign_id") if user_item else None
        )

        run_item = None
        camp_master_item = None

        if final_campaign_id:
            with ThreadPoolExecutor() as executor:
                future_run = executor.submit(
                    campaign_run_repository.get_run, final_campaign_id, run_id
                )
                future_camp = executor.submit(
                    campaign_repository.get_campaign_by_id, final_campaign_id
                )

                run_item = future_run.result()
                camp_master_item = future_camp.result()

        if not run_item or not camp_master_item:
            logger.error(
                "Data missing - Run: %s, Camp: %s",
                bool(run_item),
                bool(camp_master_item),
            )
            return {
                "statusCode": 404,
                "body": json.dumps(
                    {"status": "error", "message": "Activity not found"}
                ),
            }

        now = datetime.now(UTC).isoformat()
        deadline = run_item.get("registration_deadline")
        is_registration_closed = now > deadline if deadline else False

        response_data = {
            "status": "SUCCESS",
            "rsvp_status": user_item.get("rsvp_status", "PENDING")
            if user_item
            else "PENDING",
            "participant_name": user_item.get("name", token_name)
            if user_item
            else token_name,
            "campaign_name": camp_master_item.get("campaign_name", ""),
            "campaign_start_time": camp_master_item.get("campaign_start_time", ""),
            "campaign_location": camp_master_item.get("campaign_location", ""),
            "registration_deadline": deadline,
            "is_registration_closed": is_registration_closed,
        }

        return {"statusCode": 200, "body": json.dumps(response_data)}

    except Exception as e:
        logger.error("System Error: %s", e)
        return {
            "statusCode": 500,
            "body": json.dumps({"status": "ERROR", "message": "System busy"}),
        }