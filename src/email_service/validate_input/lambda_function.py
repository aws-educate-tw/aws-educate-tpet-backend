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
from current_user_util import current_user_util
from data_util import convert_float_to_decimal
from requests.exceptions import RequestException
from run_repository import RunRepository
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
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
DEFAULT_DISPLAY_NAME = "AWS Educate 雲端大使"
DEFAULT_REPLY_TO = "awseducate.cloudambassador@gmail.com"
DEFAULT_SENDER_LOCAL_PART = "cloudambassador"
DEFAULT_RECIPIENT_SOURCE = "SPREADSHEET"
EMAIL_PATTERN = r"[^@]+@[^@]+\.[^@]+"

# Initialize AWS clients and repositories
sqs_client = boto3.client("sqs")
run_repository = RunRepository()


def create_error_response(status_code: int, message: str) -> dict[str, Any]:
    """Create a standardized error response."""
    return {
        "statusCode": status_code,
        "body": json.dumps({"message": message}),
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
    spreadsheet_file_id: str, access_token: str, template_content: str
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
    # Identify if the incoming event is a prewarm request
    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    try:
        # Validate authorization
        access_token = validate_auth_header(event["headers"])
        if not access_token:
            return create_error_response(401, "Missing or invalid Authorization header")

        current_user_util.set_current_user_by_access_token(access_token)

        # Parse input
        body = json.loads(event.get("body", "{}"))
        recipient_source = body.get("recipient_source", DEFAULT_RECIPIENT_SOURCE)
        template_file_id = body.get("template_file_id")
        spreadsheet_file_id = body.get("spreadsheet_file_id")
        recipients = body.get("recipients", [])
        subject = body.get("subject")
        display_name = body.get("display_name", DEFAULT_DISPLAY_NAME)
        run_id = body.get("run_id") if body.get("run_id") else uuid.uuid4().hex
        attachment_file_ids = body.get("attachment_file_ids", [])
        is_generate_certificate = body.get("is_generate_certificate", False)
        reply_to = body.get("reply_to", DEFAULT_REPLY_TO)
        sender_local_part = body.get("sender_local_part", DEFAULT_SENDER_LOCAL_PART)
        cc = body.get("cc", [])
        bcc = body.get("bcc", [])

        # Validate required inputs
        if not subject:
            return create_error_response(400, "Missing email title")
        if not template_file_id:
            return create_error_response(400, "Missing template file ID")

        # Get template information
        template_info = get_file_info(template_file_id, access_token)
        template_content = get_template(template_info["s3_object_key"])

        # Process based on recipient source
        try:
            spreadsheet_info = None
            rows, columns = [], []
            if recipient_source == "SPREADSHEET":
                spreadsheet_info, rows, columns, expected_email_send_count = (
                    validate_spreadsheet_mode(
                        spreadsheet_file_id, access_token, template_content
                    )
                )
                validate_template_variables(
                    template_content, recipient_source, rows=rows
                )
            else:
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
            return create_error_response(400, str(e))

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

        if not run_repository.save_run(run_item):
            return create_error_response(500, "Failed to save run")

        # Send message to SQS
        message_body = {**common_data, "access_token": access_token}
        sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(message_body)
        )
        logger.info("Message sent to SQS: %s", message_body)

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
        logger.error("Internal server error: %s", e)
        return create_error_response(500, "Internal server error")
