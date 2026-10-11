import json
import logging
from typing import Any

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context) -> dict[str, Any]:
    """
    Lambda handler for PATCH /runs/{run_id}/schedule.

    Reschedules, cancels or immediately sends a scheduled run.

    :param event: API Gateway proxy event or a prewarm request
    :param context: Lambda context
    :return: API Gateway proxy response
    """
    aws_request_id = getattr(context, "aws_request_id", None)

    if event.get("action") == "PREWARM":
        logger.info(
            "Received a prewarm request. Skipping business logic. Request ID: %s",
            aws_request_id,
        )
        return {"statusCode": 200, "body": "Successfully warmed up"}

    logger.info(
        "Received request with pathParameters: %s. Request ID: %s",
        event.get("pathParameters"),
        aws_request_id,
    )

    # TODO: Implement reschedule, cancel and send-now for scheduled runs
    return {
        "statusCode": 501,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "message": f"update_run_schedule is not implemented yet. Request ID: {aws_request_id}"
            }
        ),
    }
