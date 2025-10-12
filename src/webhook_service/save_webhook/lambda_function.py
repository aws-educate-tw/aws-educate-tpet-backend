"""
This lambda function creates a new webhook in the DynamoDB table. The function first parses the
event body to extract the webhook details, including the webhook type, subject, display name,
template file ID, and other optional fields. The function then increments the total count for the
webhook type and generates a webhook ID and URL. The webhook details are saved to the DynamoDB
table using the WebhookRepository class. If the operation is successful, the function returns a
200 response with the webhook ID, URL, type, and creation timestamp and if errors occur during
the execution, the function logs the error and returns a 500 response.
"""

import json
import logging
import os
import uuid
from decimal import Decimal

from current_user_util import current_user_util
from time_util import get_current_utc_time
from webhook_repository import WebhookRepository
from webhook_total_count_repository import WebhookIncrementCountRepository
from webhook_type_enum import WebhookType

from email_service import EmailService

trigger_webhook_api_endpoint = os.getenv("TRIGGER_WEBHOOK_API_ENDPOINT")

webhook_repository = WebhookRepository()
webhook_increment_count_repository = WebhookIncrementCountRepository()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DEFAULT_SUBJECT = "AWS Educate 校園雲端大使活動通知"
DEFAULT_DISPLAY_NAME = "AWS Educate 校園雲端大使"
DEFAULT_REPLY_TO = "awseducate.cloudambassador@gmail.com"
DEFAULT_SENDER_LOCAL_PART = "cloudambassador"
DEFAULT_WEBHOOK_NAME_PREFIX = "TPET webhook"
DEFAULT_RUN_TYPE = "WEBHOOK"
DEFAULT_RECIPIENT_SOURCE = "DIRECT"

# Initialize services
email_service = EmailService()


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal types"""

    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def check_missing_fields(data):
    """Check if the required fields are present in the data"""
    required_fields = [
        "webhook_type",
        "template_file_id",
        "surveycake_link",
        "hash_key",
        "iv_key",
    ]
    missing_fields = [field for field in required_fields if not data.get(field)]

    return missing_fields


def lambda_handler(event, context):  # pylint: disable=unused-argument
    """Lambda function handler to create a new webhook"""
    # Validate authorization
    access_token = current_user_util.extract_bearer_token(event.get("headers", {}))
    if not access_token:
        return {
            "statusCode": 401,
            "body": json.dumps({"message": "Missing or invalid Authorization header"}),
            "headers": {"Content-Type": "application/json"},
        }

    # Get current user info
    current_user_util.set_current_user_by_access_token(access_token)
    current_user_info = current_user_util.get_current_user_info()

    # Initialize aws_request_id early
    aws_request_id = context.aws_request_id if context else "unknown"

    try:
        # Create run before saving webhook
        # Use the already extracted bearer token from the validation step above
        try:
            create_run_response = email_service.create_run(
                run_type=DEFAULT_RUN_TYPE,
                recipient_source=DEFAULT_RECIPIENT_SOURCE,
                access_token=access_token,
            )
            if not create_run_response:
                raise ValueError("Failed to create run in email service")

            logger.info("Run created successfully: %s", create_run_response)
        except (RuntimeError, ValueError) as e:
            logger.error("Failed to create run in email service: %s", str(e))
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "error": "Failed to create run in email service",
                        "message": f"Failed to create run in email service, request ID: {aws_request_id}, error: {str(e)}",
                        "request_id": aws_request_id,
                    }
                ),
            }

        # Parse the event body
        data = json.loads(event["body"])

        # Check for missing fields
        missing_fields = check_missing_fields(data)
        if missing_fields:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "status": "FAILED",
                        "message": f"Missing required fields: {missing_fields}",
                    }
                ),
            }

        # Check if webhook_type is valid
        try:
            webhook_type_enum = WebhookType(data.get("webhook_type").lower())
        except ValueError:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "status": "FAILED",
                        "message": f"Invalid webhook_type. Must be one of {[e.value for e in WebhookType]}.",
                    }
                ),
            }
        webhook_type = webhook_type_enum.value

        # Increment the total count and get the new sequence_number
        sequence_number = webhook_increment_count_repository.increment_total_count(
            webhook_type
        )

        # Generate webhook ID and URL
        webhook_id = str(uuid.uuid4())
        webhook_url = f"{trigger_webhook_api_endpoint}/{webhook_id}"

        # Use time_util to get current time
        created_at = get_current_utc_time()

        # Prepare the DynamoDB item
        item = {
            "webhook_type": webhook_type,
            "sequence_number": sequence_number,
            "webhook_id": webhook_id,
            "run_id": create_run_response.get("run_id"),
            "webhook_url": webhook_url,
            "created_at": created_at,
            "creator": current_user_info,
            "subject": data.get("subject", DEFAULT_SUBJECT),
            "display_name": data.get("display_name", DEFAULT_DISPLAY_NAME),
            "template_file_id": data.get("template_file_id"),
            "is_generate_certificate": data.get("is_generate_certificate", False),
            "reply_to": data.get("reply_to", DEFAULT_REPLY_TO),
            "sender_local_part": data.get(
                "sender_local_part", DEFAULT_SENDER_LOCAL_PART
            ),  # Optional, default is cloudambassador
            "attachment_file_ids": data.get("attachment_file_ids", []),
            "bcc": data.get("bcc", []),
            "cc": data.get("cc", []),
            "surveycake_link": data.get("surveycake_link"),
            "hash_key": data.get("hash_key"),
            "iv_key": data.get("iv_key"),
            "webhook_name": data.get(
                "webhook_name",
                f"{DEFAULT_WEBHOOK_NAME_PREFIX}-{webhook_type}-{created_at}",
            ),
        }

        # Save the item to the main table
        logger.info("Attempting to put item into DynamoDB: %s", item)
        response = webhook_repository.save_data(item)
        logger.info("DynamoDB put_item response: %s", response)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "status": "SUCCESS",
                    "message": "Webhook successfully created.",
                    "webhook_id": webhook_id,
                    "webhook_url": webhook_url,
                    "webhook_type": webhook_type,
                    "created_at": created_at,
                },
                cls=DecimalEncoder,
            ),
        }
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error occurred: %s", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"message": str(e), "request_id": aws_request_id}),
        }
