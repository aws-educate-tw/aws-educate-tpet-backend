import json
import logging
from datetime import UTC, datetime

from participant_repository import ParticipantRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

participant_repository = ParticipantRepository()


def lambda_handler(event, context):
    aws_request_id = getattr(context, "aws_request_id", None)
    logger.info("Received event: %s. Request ID: %s", event, aws_request_id)

    if event.get("action") == "PREWARM":
        logger.info(
            "Received a prewarm request. Skipping business logic. Request ID: %s",
            aws_request_id,
        )
        return {"statusCode": 200, "body": "Successfully warmed up"}
    
    try:
        path_params = event.get("pathParameters", {})
        raw_id = path_params.get("run_id_participant_id", "")

        if "_" not in raw_id:
            return build_response(
                400, {"code": "INVALID_PATH_FORMAT", "message": "Invalid ID format"}
            )

        run_id, participant_id = raw_id.rsplit("_", 1)

        item = participant_repository.get_rsvp_record(run_id, participant_id)
        if not item:
            return build_response(
                404, {"status": "error", "message": "Activity not found"}
            )

        body = json.loads(event.get("body", "{}"))
        new_status = body.get("status", "ATTEND")

        transact_items = [
            {
                "Update": {
                    "TableName": participant_repository.table_name,
                    "Key": {
                        "run_id": {"S": run_id},
                        "participant_id": {"S": participant_id},
                    },
                    "UpdateExpression": "SET #s = :s, updated_at = :u",
                    "ExpressionAttributeNames": {"#s": "status"},
                    "ExpressionAttributeValues": {
                        ":s": {"S": new_status},
                        ":u": {"S": datetime.now(UTC).isoformat()},
                    },
                }
            }
        ]

        participant_repository.update_rsvp_transaction(transact_items)

        return build_response(
            200, {"status": "SUCCESS", "data": {"current_status": new_status}}
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return build_response(
            500, {"status": "error", "message": "Internal server error"}
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
