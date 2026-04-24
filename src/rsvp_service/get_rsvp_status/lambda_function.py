import json
import os
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from campaign_repository import CampaignRepository
from participant_repository import ParticipantRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

run_repo = CampaignRepository(os.environ.get('CAMPAIGN_RUN_TABLE'))
part_repo = ParticipantRepository(os.environ.get('PARTICIPANT_TABLE'))

def lambda_handler(event, context):
    try:
        path_params = event.get('pathParameters', {})
        run_id_participant_id = path_params.get('run_id_participant_id', '')
        parts = run_id_participant_id.rsplit('_', 1)
        
        if len(parts) < 2:
            return {"statusCode": 400, "body": json.dumps({"message": "Invalid ID format"})}
        run_id, participant_id = parts[0], parts[1]

        authorizer = event.get('requestContext', {}).get('authorizer', {}).get('lambda', {})
        campaign_id_from_token = authorizer.get('campaign_id')
        token_name = authorizer.get('name', "Unknown User")

        with ThreadPoolExecutor() as executor:
            future_user = executor.submit(part_repo.get_participant, run_id, participant_id)
            user_item = future_user.result()

            final_campaign_id = campaign_id_from_token or (user_item.get('campaign_id') if user_item else None)
            
            if final_campaign_id:
                run_item = run_repo.get_run(final_campaign_id, run_id)
            else:
                run_item = run_repo.scan_run_by_id(run_id)

        if not run_item:
            return {"statusCode": 404, "body": json.dumps({"status": "error", "message": "Activity not found"})}

        now = datetime.now(timezone.utc).isoformat()
        deadline = run_item.get('registration_deadline')
        is_registration_closed = now > deadline if deadline else False

        response_data = {
            "status": "success",
            "data": {
                "current_status": user_item.get('rsvp_status', 'PENDING') if user_item else 'PENDING',
                "participant_name": user_item.get('name', token_name) if user_item else token_name,
                "run_info": {
                    "event_name": run_item.get('event_name'),
                    "event_time": run_item.get('event_time'),
                    "location": run_item.get('location'),
                    "registration_deadline": deadline,
                    "is_registration_closed": is_registration_closed 
                }
            }
        }
        return {"statusCode": 200, "body": json.dumps(response_data)}

    except Exception as e:
        logger.error(f"System Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"status": "error", "message": "System busy"})}
