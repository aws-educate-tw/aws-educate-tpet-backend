import json  # Added for parsing JSON strings
import logging
import os
import re
import time

import requests
from current_user_util import current_user_util
from email_repository import EmailRepository
from run_repository import RunRepository
from s3 import read_html_template_file_from_s3
from ses import send_email
from sqs import delete_sqs_message, get_sqs_message

from file_service import FileService

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get environment variables
SEND_EMAIL_SQS_QUEUE_URL = os.getenv("SEND_EMAIL_SQS_QUEUE_URL")
BUCKET_NAME = os.getenv("BUCKET_NAME")
ENVIRONMENT = os.environ.get("ENVIRONMENT")
DOMAIN_NAME = os.getenv("DOMAIN_NAME")

# Initialize clients and services
file_service = FileService()
email_repository = EmailRepository()
run_repository = RunRepository()


def _ensure_database_awake() -> bool:
    """
    Call health check API to ensure Aurora Serverless v2 is awake.

    :return: True if database is confirmed awake, False otherwise
    """
    health_check_url = f"https://{ENVIRONMENT}-email-service-internal-api-tpet.{DOMAIN_NAME}/{ENVIRONMENT}/email-service/health"
    max_retries = 7
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            logger.info("Attempting database health check (attempt %d/%d)", attempt + 1, max_retries)
            response = requests.get(health_check_url, timeout=5)

            if response.status_code == 200:
                logger.info("Database confirmed to be awake and healthy")
                return True
            else:
                logger.warning("Health check failed with status code: %d", response.status_code)

            # If we haven't returned yet, we need to retry
            if attempt < max_retries - 1:
                logger.info("Waiting %d seconds before retrying...", retry_delay)
                time.sleep(retry_delay)

        except Exception as e:
            logger.error("Error during database health check: %s", str(e))
            if attempt < max_retries - 1:
                logger.info("Waiting %d seconds before retrying...", retry_delay)
                time.sleep(retry_delay)

    logger.error("Database health check failed after maximum retries")
    return False


def _parse_json_field(json_string, default_value=None, field_name="field"):
    """Helper to parse JSON string fields from SQS message."""
    if isinstance(json_string, list | dict):  # Already parsed
        return json_string
    if isinstance(json_string, str):
        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            logger.warning(
                "Could not parse JSON string for %s: %s. Using default: %s",
                field_name,
                json_string,
                default_value,
            )
            return default_value
    logger.warning(
        "Unexpected type for %s: %s. Using default: %s",
        field_name,
        type(json_string),
        default_value,
    )
    return default_value


def process_email(email_data: dict) -> None:
    """
    Process email sending for a given email record.

    :param email_data: Dictionary containing complete email data including recipient and template information
    """
    recipient_email = email_data.get("recipient_email")
    email_id = email_data.get("email_id")
    run_id = email_data.get("run_id")

    logger.info("Ensuring database is awake before processing email %s", email_id)
    if not _ensure_database_awake():
        logger.error("Database unavailable while processing email %s: %s", email_id, e)
        logger.error("SQS Message for replay: %s", json.dumps(email_data))
        raise Exception("Database is not available for processing email")

    if not re.match(r"[^@]+@[^@]+\.[^@]+", recipient_email):
        logger.warning("Invalid email address provided: %s", recipient_email)
        email_repository.update_email_status(
            run_id=run_id, email_id=email_id, status="FAILED"
        )
        return

    try:
        # Get template file information and content
        template_file_info = file_service.get_file_info(
            email_data.get("template_file_id"),
            current_user_util.get_current_user_access_token(),
        )
        template_file_s3_object_key = template_file_info["s3_object_key"]
        template_content = read_html_template_file_from_s3(
            bucket=BUCKET_NAME, template_file_s3_key=template_file_s3_object_key
        )

        # Parse JSON string fields from SQS message
        row_data = _parse_json_field(
            email_data.get("row_data"), default_value={}, field_name="row_data"
        )
        attachment_file_ids = _parse_json_field(
            email_data.get("attachment_file_ids"),
            default_value=[],
            field_name="attachment_file_ids",
        )
        cc_list = _parse_json_field(
            email_data.get("cc"), default_value=[], field_name="cc"
        )
        bcc_list = _parse_json_field(
            email_data.get("bcc"), default_value=[], field_name="bcc"
        )

        # Send email
        _, status = send_email(
            subject=email_data.get("subject"),
            template_content=template_content,
            row=row_data,  # Use parsed row_data
            display_name=email_data.get("display_name"),
            reply_to=email_data.get("reply_to"),
            sender_local_part=email_data.get("sender_local_part"),
            attachment_file_ids=attachment_file_ids,  # Use parsed attachment_file_ids
            is_generate_certificate=email_data.get("is_generate_certificate"),
            run_id=run_id,
            cc=cc_list,  # Use parsed cc_list
            bcc=bcc_list,  # Use parsed bcc_list
        )

        # Update the item in PostgreSQL (formerly DynamoDB)
        email_repository.update_email_status(
            run_id=run_id, email_id=email_id, status=status
        )

        # Increment success count if email was sent successfully
        if status == "SUCCESS":
            try:
                run_repository.increment_success_email_count(run_id)
            except Exception as repo_error:
                logger.error("Error incrementing success count: %s", str(repo_error))
                raise repo_error
        elif status == "FAILED":
            try:
                run_repository.increment_failed_email_count(run_id)
            except Exception as repo_error:
                logger.error("Error incrementing failed count: %s", str(repo_error))
                raise repo_error

    except Exception as e:
        logger.error("Error processing email %s: %s", email_id, str(e))
        # Ensure status is FAILED and increment failed count before re-raising
        email_repository.update_email_status(
            run_id=run_id, email_id=email_id, status="FAILED"
        )
        try:
            run_repository.increment_failed_email_count(run_id)
        except Exception as repo_error:
            logger.error("Error incrementing failed count after exception: %s", str(repo_error))
            # Raise the repository error instead of the original error
            raise repo_error
        raise


def lambda_handler(event, context):
    """
    AWS Lambda handler function to process SQS messages for sending emails.

    :param event: The event data from SQS
    :param context: The runtime information of the Lambda function
    """
    # Log the start of Lambda execution and incoming event details
    logger.info("Lambda triggered with event: %s", event)

    # Identify if the incoming event is a prewarm request
    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    for record in event["Records"]:
        try:
            sqs_message = get_sqs_message(record)
            access_token = sqs_message["access_token"]

            # Set the current user information
            current_user_util.set_current_user_by_access_token(access_token)

            # Process the email
            process_email(sqs_message)

            logger.info(
                "Successfully processed email for run_id: %s", sqs_message.get("run_id")
            )

        except Exception as e:
            logger.error("Error processing message: %s", e)
            raise
        finally:
            if SEND_EMAIL_SQS_QUEUE_URL:
                try:
                    delete_sqs_message(
                        SEND_EMAIL_SQS_QUEUE_URL,
                        sqs_message["receipt_handle"],
                    )
                    logger.info(
                        "Deleted message from SQS: %s", sqs_message["receipt_handle"]
                    )
                except Exception as e:
                    logger.error("Error deleting SQS message: %s", e)
            else:
                logger.error(
                    "SQS_QUEUE_URL is not available: %s", SEND_EMAIL_SQS_QUEUE_URL
                )
