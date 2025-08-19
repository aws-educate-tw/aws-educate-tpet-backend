import io
import json
import logging
import os
import re
import uuid
from typing import Any

import boto3
import pandas as pd
import requests
from botocore.exceptions import ClientError
from current_user_util import current_user_util
from data_util import convert_float_to_decimal
from requests.exceptions import RequestException
from run_repository import RunRepository
from sqs import send_message_to_queue
from time_util import get_current_utc_time

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Constants
BUCKET_NAME = os.getenv("BUCKET_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT")
FILE_SERVICE_API_BASE_URL = (
    f"https://{ENVIRONMENT}-file-service-internal-api-tpet.aws-educate.tw/{ENVIRONMENT}"
)
CREATE_EMAIL_SQS_QUEUE_URL = os.getenv("CREATE_EMAIL_SQS_QUEUE_URL")
DEFAULT_DISPLAY_NAME = "AWS Educate 雲端大使"
DEFAULT_REPLY_TO = "awseducate.cloudambassador@gmail.com"
DEFAULT_SENDER_LOCAL_PART = "cloudambassador"
DEFAULT_RECIPIENT_SOURCE = "SPREADSHEET"
DEFAULT_RUN_TYPE = "EMAIL"
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


def validate_auth_header(headers: dict[str, str]) -> str | None:
    """Validate authorization header and return access token."""
    authorization_header = headers.get("authorization")
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return None
    return authorization_header.split(" ")[1]


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


def get_template(template_file_s3_key: str) -> str:
    """Retrieve template content from S3 bucket."""
    try:
        s3 = boto3.client("s3")
        request = s3.get_object(Bucket=BUCKET_NAME, Key=template_file_s3_key)
        return request["Body"].read().decode("utf-8")
    except Exception as e:
        logger.error("Error in get_template: %s", e)
        raise


def read_sheet_data_from_s3(
    spreadsheet_file_s3_key: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Read Excel sheet data from S3 bucket."""
    try:
        s3 = boto3.client("s3")
        request = s3.get_object(Bucket=BUCKET_NAME, Key=spreadsheet_file_s3_key)
        xlsx_content = request["Body"].read()
        excel_data = pd.read_excel(io.BytesIO(xlsx_content), engine="openpyxl")
        rows = excel_data.to_dict(orient="records")
        if excel_data.empty:
            return [], []
        return rows, excel_data.columns.tolist()
    except Exception as e:
        logger.error("Error in read excel from s3: %s", e)
        raise


def extract_template_variables(template_content: str) -> list[str]:
    """Extract required variables from template content.

    Args:
        template_content: The content of template file.

    Returns:
        A list of variable names that are required in the template.
    """
    try:
        placeholders = re.findall(r"{{(.*?)}}", template_content)
        return list(set(placeholders))  # Use set to remove duplicates
    except Exception as e:
        logger.error("Error in extract_template_variables: %s", e)
        raise


## TODO - valaidate_run_type


def validate_template_variables(
    template_content: str,
    recipient_source: str,
    recipients: list[dict[str, Any]] | None = None,
    rows: list[dict[str, Any]] | None = None,
) -> None:
    """Validate that all required template variables are provided.

    Args:
        template_content: The content of template file.
        recipient_source: The source of recipients (SPREADSHEET or DIRECT).
        recipients: List of recipients with their template variables (for DIRECT mode).
        rows: List of spreadsheet rows (for SPREADSHEET mode).

    Raises:
        ValueError: If any recipient is missing required template variables.
    """
    required_variables = extract_template_variables(template_content)
    if not required_variables:
        return

    if recipient_source == "DIRECT":
        for recipient in recipients or []:
            template_vars = recipient.get("template_variables", {})
            missing_vars = [
                var for var in required_variables if var not in template_vars
            ]
            if missing_vars:
                raise ValueError(
                    f"Email {recipient['email']} missing required template variables: {', '.join(missing_vars)}"
                )
    else:  # SPREADSHEET mode
        for index, row in enumerate(rows or [], start=1):
            missing_vars = [var for var in required_variables if var not in row]
            if missing_vars:
                raise ValueError(
                    f"Row {index} (Email: {row.get('Email', 'N/A')}) missing required template variables: {', '.join(missing_vars)}"
                )


def validate_spreadsheet_mode(
    spreadsheet_file_id: str, access_token: str
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str], int]:
    """Validate spreadsheet mode specific requirements."""
    if not spreadsheet_file_id:
        raise ValueError("Missing spreadsheet file ID")

    spreadsheet_info = get_file_info(spreadsheet_file_id, access_token)
    spreadsheet_s3_key = spreadsheet_info["s3_object_key"]
    rows, columns = read_sheet_data_from_s3(spreadsheet_s3_key)

    # Validate email format
    invalid_emails = [
        {"row": index, "email": row.get("Email")}
        for index, row in enumerate(rows, start=1)
        if not row.get("Email") or not re.match(EMAIL_PATTERN, row.get("Email"))
    ]
    if invalid_emails:
        raise ValueError(f"Invalid email(s) in spreadsheet: {invalid_emails}")

    expected_email_send_count = len([row for row in rows if row.get("Email")])
    return spreadsheet_info, rows, columns, expected_email_send_count


def validate_direct_mode(recipients: list[dict[str, Any]]) -> int:
    """Validate direct mode specific requirements."""
    if not recipients:
        raise ValueError("Missing recipients list")

    # Validate email format
    invalid_recipients = [
        recipient["email"]
        for recipient in recipients
        if not re.match(EMAIL_PATTERN, recipient.get("email", ""))
    ]
    if invalid_recipients:
        raise ValueError(f"Invalid email(s) in recipients list: {invalid_recipients}")

    return len(recipients)


def validate_certificate_requirements(
    is_generate_certificate: bool,
    recipient_source: str,
    recipients: list[dict[str, Any]],
    columns: list[str],
) -> None:
    """Validate certificate generation requirements."""
    if not is_generate_certificate:
        return

    required_fields = ["Name", "Certificate Text"]
    if recipient_source == "DIRECT":
        for recipient in recipients:
            template_vars = recipient.get("template_variables", {})
            missing_fields = [
                field for field in required_fields if field not in template_vars
            ]
            if missing_fields:
                raise ValueError(
                    f"Email {recipient['email']} missing required fields for certificate generation: {', '.join(missing_fields)}"
                )
    else:
        missing_required_columns = [
            col for col in required_fields if col not in columns
        ]
        if missing_required_columns:
            raise ValueError(
                f"Missing required columns for certificate generation: {', '.join(missing_required_columns)}"
            )


def validate_email_addresses(emails: list[str], reply_to: str) -> None:
    """Validate email formats for cc, bcc, and reply_to."""
    for email in emails:
        if not re.match(EMAIL_PATTERN, email):
            raise ValueError(f"Invalid email format: {email}")

    if not re.match(EMAIL_PATTERN, reply_to):
        raise ValueError(f"Invalid email format: {reply_to}")


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
            spreadsheet_info if recipient_source == "SPREADSHEET" else None
        ),
        "attachment_files": attachment_files,
        "sender": current_user_info,
    }
    return convert_float_to_decimal(run_item)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Main Lambda function handler."""
    # Initialize aws_request_id early
    aws_request_id = context.aws_request_id if context else "unknown"
    error_responder = ErrorResponder(aws_request_id)

    # Identify if the incoming event is a prewarm request
    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    try:
        # Validate authorization
        access_token = validate_auth_header(event["headers"])
        if not access_token:
            return error_responder.create_error_response(
                401, "Missing or invalid Authorization header"
            )

        current_user_util.set_current_user_by_access_token(access_token)

        # Parse input
        body = json.loads(event.get("body", "{}"))
        recipient_source = body.get("recipient_source", DEFAULT_RECIPIENT_SOURCE)
        run_type = body.get("run_type", DEFAULT_RUN_TYPE)
        template_file_id = body.get("template_file_id")
        spreadsheet_file_id = body.get("spreadsheet_file_id")
        recipients = body.get("recipients", [])
        subject = body.get("subject")
        display_name = body.get("display_name", DEFAULT_DISPLAY_NAME)
        run_id = body.get("run_id")
        attachment_file_ids = body.get("attachment_file_ids", [])
        is_generate_certificate = body.get("is_generate_certificate", False)
        reply_to = body.get("reply_to", DEFAULT_REPLY_TO)
        sender_local_part = body.get("sender_local_part", DEFAULT_SENDER_LOCAL_PART)
        cc = body.get("cc", [])
        bcc = body.get("bcc", [])

        # --- Webhook specific logic ---
        if run_type == "WEBHOOK":
            logger.info(
                "Processing WEBHOOK run type with run_id: %s and recipients: %s",
                run_id,
                recipients,
            )
            # Validate WEBHOOK run_type
            if not run_id:
                return error_responder.create_error_response(
                    400, "Missing run_id for WEBHOOK run_type"
                )
            if recipient_source != "DIRECT":
                return error_responder.create_error_response(
                    400, "WEBHOOK run_type only supports DIRECT recipient source"
                )

            # For webhook append mode, validation is based on the request body,
            # not the parent run. The run_id is only for grouping.
            if not run_repository.get_run_by_id(run_id):
                return error_responder.create_error_response(
                    404, f"Run with ID {run_id} not found."
                )

            try:
                # Validate required inputs from the body
                if not subject:
                    raise ValueError("Missing email subject")
                if not template_file_id:
                    raise ValueError("Missing template file ID")

                # Reuse existing validation functions
                validate_direct_mode(recipients)
                template_info = get_file_info(template_file_id, access_token)
                template_content = get_template(template_info["s3_object_key"])
                validate_template_variables(
                    template_content, "DIRECT", recipients=recipients
                )
                validate_certificate_requirements(
                    is_generate_certificate, "DIRECT", recipients=recipients, columns=[]
                )
                validate_email_addresses(cc + bcc, reply_to)

            except (ValueError, RequestException) as e:
                return error_responder.create_error_response(400, str(e))

            # If validation passes, increment the counter atomically
            if not run_repository.increment_expected_email_send_count(run_id):
                return error_responder.create_error_response(
                    404, f"Run with ID {run_id} not found for counter increment."
                )

            # Prepare message body for SQS using data from the request body
            current_user_info = current_user_util.get_current_user_info()
            sender_id = current_user_info.get("user_id")

            message_body = {
                "run_id": run_id,
                "run_type": "WEBHOOK",
                "recipient_source": "DIRECT",
                "recipients": recipients,
                "subject": subject,
                "template_file_id": template_file_id,
                "attachment_file_ids": attachment_file_ids,
                "is_generate_certificate": is_generate_certificate,
                "sender_id": sender_id,
                "reply_to": reply_to,
                "sender_local_part": sender_local_part,
                "display_name": display_name,
                "cc": cc,
                "bcc": bcc,
                "access_token": access_token,
            }

            try:
                if not CREATE_EMAIL_SQS_QUEUE_URL:
                    raise ValueError(
                        "CREATE_EMAIL_SQS_QUEUE_URL environment variable not set."
                    )
                send_message_to_queue(CREATE_EMAIL_SQS_QUEUE_URL, message_body)
                logger.info("Webhook message sent to SQS for run_id: %s", run_id)
            except (ClientError, ValueError) as e:
                logger.error("Failed to send webhook message to SQS: %s", e)
                return error_responder.create_error_response(
                    500, "Failed to queue email request after validation."
                )

            return {
                "statusCode": 202,
                "body": json.dumps(
                    {
                        "status": "SUCCESS",
                        "message": "Your email request has been successfully received.",
                        "run_id": run_id,
                    }
                ),
                "headers": {"Content-Type": "application/json"},
            }

        # --- Default logic for non-WEBHOOK run type ---
        else:
            # Validate required inputs
            if not subject:
                return error_responder.create_error_response(
                    400, "Missing email subject"
                )
            if not template_file_id:
                return error_responder.create_error_response(
                    400, "Missing template file ID"
                )
            if run_id:
                return error_responder.create_error_response(
                    400, "run_id should not be provided for non-WEBHOOK run type"
                )

            # Generate a new run_id
            run_id = uuid.uuid4().hex

            # Get template information
            template_info = get_file_info(template_file_id, access_token)
            template_content = get_template(template_info["s3_object_key"])

            # Process based on recipient source
            try:
                spreadsheet_info = None
                rows, columns = [], []
                if recipient_source == "SPREADSHEET":
                    spreadsheet_info, rows, columns, expected_email_send_count = (
                        validate_spreadsheet_mode(spreadsheet_file_id, access_token)
                    )
                    validate_template_variables(
                        template_content, recipient_source, rows=rows
                    )
                else:  # DIRECT mode
                    expected_email_send_count = validate_direct_mode(recipients)
                    validate_template_variables(
                        template_content, recipient_source, recipients=recipients
                    )

                # Validate certificate requirements
                validate_certificate_requirements(
                    is_generate_certificate, recipient_source, recipients, columns
                )

                # Validate email addresses
                validate_email_addresses(cc + bcc, reply_to)

            except ValueError as e:
                return error_responder.create_error_response(400, str(e))

        # Get current user info
        current_user_info = current_user_util.get_current_user_info()
        sender_id = current_user_info.get("user_id")

        # Get attachment file information
        attachment_files = [
            get_file_info(file_id, access_token) for file_id in attachment_file_ids
        ]

        # Prepare common data
        common_data = {
            "recipient_source": recipient_source,
            "run_type": run_type,
            "run_id": run_id,
            "template_file_id": template_file_id,
            "spreadsheet_file_id": (
                spreadsheet_file_id if recipient_source == "SPREADSHEET" else None
            ),
            "subject": subject,
            "display_name": display_name,
            "attachment_file_ids": attachment_file_ids,
            "is_generate_certificate": is_generate_certificate,
            "sender_id": sender_id,
            "reply_to": reply_to,
            "sender_local_part": sender_local_part,
            "cc": cc,
            "bcc": bcc,
            "recipients": recipients if recipient_source == "DIRECT" else [],
            "success_email_count": 0,
            "expected_email_send_count": expected_email_send_count,
        }

        # Prepare and save run item
        run_item = prepare_run_data(
            recipient_source,
            common_data,
            template_info,
            spreadsheet_info,
            attachment_files,
            current_user_info,
        )

        if not run_repository.upsert_run(run_item):
            return error_responder.create_error_response(
                500, f"Failed to save run: {run_item['run_id']}"
            )

        # Send message to SQS
        message_body = {**common_data, "access_token": access_token}
        try:
            if not CREATE_EMAIL_SQS_QUEUE_URL:
                raise ValueError(
                    "CREATE_EMAIL_SQS_QUEUE_URL environment variable not set."
                )
            send_message_to_queue(CREATE_EMAIL_SQS_QUEUE_URL, message_body)
            logger.info("Message sent to SQS: %s", message_body)
        except (ClientError, ValueError) as e:
            logger.error("Failed to send message to SQS: %s", e)
            return error_responder.create_error_response(
                500, "Failed to queue email request"
            )

        # Prepare success response
        return {
            "statusCode": 202,
            "body": json.dumps(
                {
                    "status": "SUCCESS",
                    "message": "Your send email request has been successfully received and is being processed.",
                    **common_data,
                }
            ),
            "headers": {"Content-Type": "application/json"},
        }

    except Exception as e:
        logger.error("Request ID: %s, Internal server error: %s", aws_request_id, e)
        return error_responder.create_error_response(
            500, "Please try again later or contact support"
        )
