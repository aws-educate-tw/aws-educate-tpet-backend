import logging
from typing import Any

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context) -> dict[str, Any]:
    """
    Lambda handler for dispatching a scheduled run.

    Invoked by EventBridge Scheduler when a scheduled run is due, or invoked
    asynchronously by update_run_schedule when a scheduled run is sent
    immediately. The payload only contains the run_id.

    :param event: {"run_id": "..."} or a prewarm request
    :param context: Lambda context
    :return: Response with status code and body
    """
    logger.info("Lambda triggered with event: %s", event)

    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    # TODO: Wake up Aurora, claim the run and push its SCHEDULED emails to the send_email queue
    logger.warning(
        "dispatch_scheduled_run is not implemented yet. run_id: %s",
        event.get("run_id"),
    )
    return {"statusCode": 501, "body": "dispatch_scheduled_run is not implemented yet"}
