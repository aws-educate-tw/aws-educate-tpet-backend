import io
import json
import logging
import requests
from typing import Any, cast
import os
import re
import uuid

from data_util import convert_float_to_decimal
from recipient_source_enum import RecipientSource
from run_repository import RunRepository
from current_user_util import current_user_util
from run_type_enum import RunType
from time_util import get_current_utc_time
from requests.exceptions import RequestException
from sqs import delete_sqs_message, get_sqs_message, send_message_to_queue


# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Constants
BUCKET_NAME = os.getenv("BUCKET_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT")
FILE_SERVICE_API_BASE_URL = (
    f"https://{ENVIRONMENT}-file-service-internal-api-tpet.aws-educate.tw/{ENVIRONMENT}"
)
UPSERT_RUN_SQS_QUEUE_URL = os.getenv("UPSERT_RUN_SQS_QUEUE_URL")
DEFAULT_DISPLAY_NAME = "AWS Educate 雲端大使"
DEFAULT_REPLY_TO = "awseducate.cloudambassador@gmail.com"
DEFAULT_SENDER_LOCAL_PART = "cloudambassador"
DEFAULT_RECIPIENT_SOURCE = RecipientSource.SPREADSHEET.value
DEFAULT_RUN_TYPE = RunType.EMAIL.value
EMAIL_PATTERN = r"[^@]+@[^@]+\.[^@]+"

# Initialize repositories
run_repository = RunRepository()


class ErrorResponder:
    """A helper class to create standardized error responses with a request ID."""

    def __init__(self, request_id: str):
        self._request_id = request_id

    def create_error_response(self, status_code: int, message: str) -> dict[str, Any]:
        """Creates a standardized error response."""
        error_body = {
            "message": f"{message}, Request ID: {self._request_id}",
            "request_id": self._request_id,
        }
        return {
            "statusCode": status_code,
            "body": json.dumps(error_body),
            "headers": {"Content-Type": "application/json"},
        }

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
    run_data: dict[str, Any],
    current_user_info: dict[str, Any],
) -> dict[str, Any]:
    """Prepare run item data."""
    created_at = get_current_utc_time()
    run_item = {
        **run_data,
        "created_at": created_at,
        "created_year": created_at[:4],
        "created_year_month": created_at[:7],
        "created_year_month_day": created_at[:10],
        "sender": current_user_info,
    }
    return cast(dict[str, Any], convert_float_to_decimal(run_item))


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Main Lambda function handler for upsert run operations."""
    logger.info("Lambda triggered with event: %s", event)

    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}
    

    # Initialize aws_request_id early
    aws_request_id = context.aws_request_id if context else "unknown"
    error_responder = ErrorResponder(aws_request_id)

    # Identify if the incoming event is a prewarm request
    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    try:
        for record in event["Records"]:
            sqs_message = None
            try:
                sqs_message = get_sqs_message(record)
            except Exception as e:
                logger.error("Error getting SQS message: %s", e)
                continue

            try:
                message_body = json.loads(sqs_message["body"])
                access_token = message_body.pop("access_token")
                common_data = message_body
                current_user_util.set_current_user_by_access_token(access_token)
                current_user_info = current_user_util.get_current_user_info()
                recipient_source = common_data["recipient_source"]
                template_file_id = common_data["template_file_id"]
                spreadsheet_file_id = common_data.get("spreadsheet_file_id")
                attachment_file_ids = common_data.get("attachment_file_ids", [])

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
                    common_data,
                    template_info,
                    spreadsheet_info,
                    attachment_files,
                    current_user_info,
                )

                if not run_repository.upsert_run(run_item):
                    raise RuntimeError(f"Failed to save run: {run_item['run_id']}")
            except Exception as e:
                logger.error("Request ID: %s, Error processing record: %s", aws_request_id, e)
                continue
            finally:
                if sqs_message and UPSERT_RUN_SQS_QUEUE_URL:
                    try:
                        delete_sqs_message(
                            UPSERT_RUN_SQS_QUEUE_URL,
                            sqs_message["receipt_handle"],
                        )
                        logger.info(
                            "Deleted message from SQS: %s", sqs_message["receipt_handle"]
                        )
                    except Exception as e:
                        logger.error("Error deleting SQS message: %s", e)
                elif not UPSERT_RUN_SQS_QUEUE_URL:
                    logger.error(
                        "UPSERT_RUN_SQS_QUEUE_URL is not available: %s",
                        UPSERT_RUN_SQS_QUEUE_URL,
                    )
        
        return {"statusCode": 200, "body": json.dumps({"status": "SUCCESS"})}

    except Exception as e:
        logger.error("Request ID: %s, Internal server error: %s", aws_request_id, e)
        return error_responder.create_error_response(
            500, "Please try again later or contact support"
        )
