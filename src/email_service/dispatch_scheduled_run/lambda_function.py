import logging
import os
from typing import Any

import boto3
from email_repository import EmailRepository
from run_repository import RunRepository
from run_status_enum import RunStatus
from sqs import send_message_to_queue

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get environment variables
SEND_EMAIL_SQS_QUEUE_URL = os.getenv("SEND_EMAIL_SQS_QUEUE_URL")
AUTO_RESUME_AURORA_LAMBDA_NAME = os.getenv("AUTO_RESUME_AURORA_LAMBDA_NAME")

# Calculate batch size to avoid RDS Data API 1MB limit
RDS_DATA_API_SAFE_BATCH_SIZE = 500  # Safe limit to avoid 1MB response size

# Initialize clients and repositories
lambda_client = boto3.client("lambda")
run_repository = RunRepository()
email_repository = EmailRepository()


def ensure_db_ready() -> None:
    """Sync invoke auto_resume Lambda to ensure Aurora is awake before DB access."""
    logger.info("Start invoke auto_resume Lambda to ensure Aurora is awake.")
    response = lambda_client.invoke(
        FunctionName=AUTO_RESUME_AURORA_LAMBDA_NAME,
        InvocationType="RequestResponse",
        Payload=b"{}",
    )
    if response["StatusCode"] != 200 or "FunctionError" in response:
        logger.error("auto_resume invocation failed: %s", response)
        raise RuntimeError("Database wake-up failed")


def build_send_email_message(run_id: str, email: dict) -> dict:
    """
    Build the send_email SQS message for a scheduled email.

    It has the same fields as the message create_email sends for immediate
    runs, so send_email handles scheduled and immediate emails the same way.

    :param run_id: The ID of the run
    :param email: The scheduled email read from the database
    :return: The message to send to the send email queue
    """
    return {
        "run_id": run_id,
        "email_id": email["email_id"],
        "recipient_email": email["recipient_email"],
        "subject": email["subject"],
        "template_file_id": email["template_file_id"],
        "display_name": email["display_name"],
        "row_data": email["row_data"],
        "attachment_file_ids": email["attachment_file_ids"],
        "is_generate_certificate": email["is_generate_certificate"],
        "sender_id": email["sender_id"],
        "reply_to": email.get("reply_to"),
        "sender_local_part": email.get("sender_local_part"),
        "cc": email.get("cc"),
        "bcc": email.get("bcc"),
    }


def enqueue_scheduled_email(run_id: str, email: dict) -> bool:
    """
    Push a scheduled email to the send email queue, then mark it PENDING.

    An email that can't be queued is marked FAILED and counted as failed here,
    because send_email will never process it.

    :param run_id: The ID of the run
    :param email: The scheduled email read from the database
    :return: True if the email was queued, False otherwise
    """
    email_id = email["email_id"]
    message = build_send_email_message(run_id, email)

    try:
        send_message_to_queue(SEND_EMAIL_SQS_QUEUE_URL, message)
    except Exception as e:
        logger.error("Failed to queue email %s for sending: %s", email_id, e)
        if email_repository.mark_scheduled_email_failed(run_id, email_id):
            run_repository.increment_failed_email_count(run_id)
        return False

    email_repository.mark_scheduled_email_pending(run_id, email_id)
    return True


def fetch_all_scheduled_emails(run_id: str) -> list[dict]:
    """
    Read every SCHEDULED email of a run in batches, the same way list_emails
    fetches large requests.

    All emails are read before any of them is dispatched, so the SCHEDULED
    emails don't change between batches and the offsets stay valid.

    :param run_id: The ID of the run
    :return: List of SCHEDULED emails
    """
    all_emails = []
    current_offset = 0

    while True:
        logger.info(
            "Fetching batch: offset=%d, limit=%d",
            current_offset,
            RDS_DATA_API_SAFE_BATCH_SIZE,
        )
        batch_emails = email_repository.list_scheduled_emails(
            run_id, RDS_DATA_API_SAFE_BATCH_SIZE, current_offset
        )
        all_emails.extend(batch_emails)

        # If we got fewer items than batch size, we've reached the end
        if len(batch_emails) < RDS_DATA_API_SAFE_BATCH_SIZE:
            break
        current_offset += len(batch_emails)

    return all_emails


def dispatch_scheduled_emails(run_id: str) -> tuple[int, int]:
    """
    Push every SCHEDULED email of a run to the send email queue.

    Only SCHEDULED emails are read, so a retry after a partial dispatch pushes
    only the emails that weren't pushed yet. An email is marked PENDING only
    after it is queued, so running this again never misses an email, but an
    email queued right before the invocation stopped can be queued again.

    :param run_id: The ID of the run
    :return: The number of emails queued and the number that failed to queue
    """
    scheduled_emails = fetch_all_scheduled_emails(run_id)
    logger.info("Found %d scheduled email(s) for run %s", len(scheduled_emails), run_id)

    queued_count = 0
    failed_count = 0
    for email in scheduled_emails:
        if enqueue_scheduled_email(run_id, email):
            queued_count += 1
        else:
            failed_count += 1

    return queued_count, failed_count


def dispatch_run(run_id: str | None) -> dict[str, Any]:
    """
    Claim a run and push its SCHEDULED emails to the send email queue.

    :param run_id: The ID of the run to dispatch, from the event payload
    :return: Response with status code and body
    """
    if not run_id:
        raise ValueError("run_id is required")

    ensure_db_ready()

    # A run that is already SENDING was sent immediately by update_run_schedule,
    # or this is a retry after a partial dispatch
    claimed = run_repository.claim_scheduled_run(run_id)
    run_status = run_repository.get_run_status(run_id)

    if run_status is None:
        raise ValueError(f"Run with ID {run_id} not found.")

    if run_status != RunStatus.SENDING.value:
        logger.info("Run %s is %s. Skipping dispatch.", run_id, run_status)
        return {
            "statusCode": 200,
            "body": f"Run is {run_status}, nothing to dispatch",
        }

    logger.info(
        "Dispatching run %s: %s",
        run_id,
        "claimed from SCHEDULED" if claimed else "already SENDING",
    )
    queued_count, failed_count = dispatch_scheduled_emails(run_id)

    # send_email finalizes the run after every email it processes, but emails
    # that failed to queue never reach send_email, so the run would stay
    # SENDING if the last email failed here
    run_repository.finalize_run_status_if_complete(run_id)

    logger.info(
        "Dispatched run %s: %d email(s) queued, %d failed to queue",
        run_id,
        queued_count,
        failed_count,
    )
    return {
        "statusCode": 200,
        "body": f"Dispatched run {run_id}: {queued_count} email(s) queued, {failed_count} failed to queue",
    }


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

    run_id = event.get("run_id")

    try:
        return dispatch_run(run_id)
    except Exception as e:
        # Raise on failure instead of returning an error response, otherwise Lambda won't retry it
        logger.error("Error dispatching run %s: %s", run_id, e)
        raise
