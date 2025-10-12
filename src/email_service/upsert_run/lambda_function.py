import logging
import os
from typing import Any, cast

import requests
from current_user_util import current_user_util
from data_util import convert_float_to_decimal
from recipient_source_enum import RecipientSource
from requests.exceptions import RequestException
from run_repository import RunRepository
from run_type_enum import RunType
from sqs import get_sqs_message, send_message_to_queue
from time_util import get_current_utc_time

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Constants
BUCKET_NAME = os.getenv("BUCKET_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT")
DOMAIN_NAME = os.getenv("DOMAIN_NAME")
FILE_SERVICE_API_BASE_URL = (
    f"https://{ENVIRONMENT}-file-service-internal-api-tpet.{DOMAIN_NAME}/{ENVIRONMENT}"
)
CREATE_EMAIL_SQS_QUEUE_URL = os.getenv("CREATE_EMAIL_SQS_QUEUE_URL")
UPSERT_RUN_SQS_QUEUE_URL = os.getenv("UPSERT_RUN_SQS_QUEUE_URL")
DEFAULT_DISPLAY_NAME = "AWS Educate 雲端大使"
DEFAULT_REPLY_TO = "awseducate.cloudambassador@gmail.com"
DEFAULT_SENDER_LOCAL_PART = "cloudambassador"
DEFAULT_RECIPIENT_SOURCE = RecipientSource.SPREADSHEET.value
DEFAULT_RUN_TYPE = RunType.EMAIL.value
EMAIL_PATTERN = r"[^@]+@[^@]+\.[^@]+"

# Initialize repositories
run_repository = RunRepository()


def get_file_info(file_id: str, access_token: str) -> dict[str, Any]:
    """Retrieve file information from the file service API."""
    try:
        api_url = f"{FILE_SERVICE_API_BASE_URL}/files/{file_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        response = requests.get(url=api_url, headers=headers, timeout=25)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.error("Request timed out for file_id: %s", file_id)
        raise
    except RequestException as e:
        logger.error("Error in get_file_info: %s", e)
        raise


def prepare_run_data(
    recipient_source: str,
    common_data: dict[str, Any],
    template_info: dict[str, Any],
    spreadsheet_info: dict[str, Any] | None,
    attachment_files: list[dict[str, Any]],
    current_user_info: dict[str, Any],
) -> dict[str, Any]:
    """Prepare run item data."""
    created_at = get_current_utc_time()
    run_item = {
        **common_data,
        "created_at": created_at,
        "created_year": created_at[:4],
        "created_year_month": created_at[:7],
        "created_year_month_day": created_at[:10],
        "template_file": template_info,
        "spreadsheet_file": (
            spreadsheet_info
            if recipient_source == RecipientSource.SPREADSHEET.value
            else None
        ),
        "attachment_files": attachment_files,
        "sender": current_user_info,
    }
    return cast(dict[str, Any], convert_float_to_decimal(run_item))


def forward_message_to_target_queue(
    message: dict[str, Any], target_queue_url: str
) -> bool:
    """
    Forward a message from auto-resumer queue to a target queue.

    :param message: The SQS message to forward
    :return: True if message was forwarded successfully, False otherwise
    """
    try:
        logger.info("Forwarding message to target SQS queue")
        send_message_to_queue(target_queue_url, message)
        logger.info("Successfully forwarded message to target SQS queue")
    except Exception as e:
        logger.error("Failed to forward message to target SQS queue: %s", str(e))
        raise


def process_record(record: dict[str, Any], aws_request_id: str) -> None:
    """
    Process a single SQS record.

    :param record: The SQS record to process
    :param aws_request_id: The AWS request ID for logging
    :raises: Exception if processing fails
    """
    sqs_message = get_sqs_message(record)

    run_id = sqs_message["run_id"]
    run_type = sqs_message["run_type"]

    access_token = sqs_message.pop("access_token")
    receipt_handle = sqs_message.pop("receipt_handle")

    # Validate run type if webhook
    if run_type == RunType.WEBHOOK.value:
        existing_run = run_repository.get_run_by_id(run_id)
        if not existing_run:
            raise ValueError(f"Run with ID {run_id} not found.")
        if existing_run.get("run_type") != RunType.WEBHOOK.value:
            raise ValueError(
                f"Run with ID {run_id} is not a WEBHOOK run type, "
                f"but {existing_run.get('run_type')}"
            )
    current_user_util.set_current_user_by_access_token(access_token)
    current_user_info = current_user_util.get_current_user_info()
    recipient_source = sqs_message["recipient_source"]
    template_file_id = sqs_message["template_file_id"]
    spreadsheet_file_id = sqs_message.get("spreadsheet_file_id")
    attachment_file_ids = sqs_message.get("attachment_file_ids", [])

    template_info = get_file_info(template_file_id, access_token)
    spreadsheet_info = (
        get_file_info(spreadsheet_file_id, access_token)
        if recipient_source == RecipientSource.SPREADSHEET.value and spreadsheet_file_id
        else None
    )
    attachment_files = [
        get_file_info(file_id, access_token) for file_id in attachment_file_ids
    ]

    run_item = prepare_run_data(
        recipient_source,
        sqs_message,
        template_info,
        spreadsheet_info,
        attachment_files,
        current_user_info,
    )

    if not run_repository.upsert_run(run_item):
        raise RuntimeError(f"Failed to save run: {run_item['run_id']}")

    # Forward the message to upsert_run SQS queue
    forward_message = {
        **sqs_message,
        "access_token": access_token,
        "receipt_handle": receipt_handle,
    }

    forward_message_to_target_queue(forward_message, CREATE_EMAIL_SQS_QUEUE_URL)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Main Lambda function handler for upsert run operations."""
    logger.info("Lambda triggered with event: %s", event)

    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    batch_item_failures = []

    for record in event["Records"]:
        try:
            process_record(record, context.aws_request_id)
        except Exception as e:
            logger.error("Error processing record: %s", e)
            batch_item_failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": batch_item_failures}
