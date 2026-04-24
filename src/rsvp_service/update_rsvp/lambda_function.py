import json
import logging
import os
from datetime import datetime, timezone  
from rsvp_repository import RSVPRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

repo = RSVPRepository()

def lambda_handler(event, context):
    try:
        authorizer = event.get("requestContext", {}).get("authorizer", {}).get("lambda", {})
        if not authorizer:
            logger.warning("Authorizer data is missing, check API Gateway configuration.")
        
        email = authorizer.get("email", "unknown_user")
        
        path_params = event.get("pathParameters", {})
        raw_id = path_params.get("run_id_participant_id", "")
        if "_" not in raw_id:
            return build_response(400, {"code": "INVALID_PATH_FORMAT", "message": "Invalid ID format"})
        
        run_id, participant_id = raw_id.rsplit("_", 1)

        item = repo.get_rsvp_record(run_id, participant_id)
        if not item:
            return build_response(404, {"status": "error", "message": "Activity not found"})
        now = datetime.now(timezone.utc).isoformat()
        return build_response(200, {"status": "SUCCESS", "data": {"current_status": "ATTEND"}})

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}") # 使用 logger.error
        return build_response(500, {"status": "error", "message": "Internal server error"})

def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }