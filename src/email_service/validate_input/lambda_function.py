import io
import json
import logging
import os
import re
import uuid
from typing import Any, cast

import boto3
import pandas as pd
import requests
from botocore.exceptions import ClientError
from current_user_util import current_user_util
from data_util import convert_float_to_decimal
from error_code_enum import SystemErrorCode, ValidationErrorCode
from recipient_source_enum import RecipientSource
from requests.exceptions import RequestException
from run_type_enum import RunType
from sqs import send_message_to_queue
from time_util import get_current_utc_time
from validation_exceptions import ValidationError, ValidationErrorCollector

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Constants
BUCKET_NAME = os.getenv("BUCKET_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT")
FILE_SERVICE_API_BASE_URL = (
    f"https://{ENVIRONMENT}-file-service-internal-api-tpet.aws-educate.tw/{ENVIRONMENT}"
)
AUTO_RESUMER_SQS_QUEUE_URL = os.getenv("AUTO_RESUMER_SQS_QUEUE_URL")
DEFAULT_DISPLAY_NAME = "AWS Educate 雲端大使"
DEFAULT_REPLY_TO = "awseducate.cloudambassador@gmail.com"
DEFAULT_SENDER_LOCAL_PART = "cloudambassador"
DEFAULT_RECIPIENT_SOURCE = RecipientSource.SPREADSHEET.value
DEFAULT_RUN_TYPE = RunType.EMAIL.value
EMAIL_PATTERN = r"[^@]+@[^@]+\.[^@]+"


class ErrorResponder:
    """A helper class to create standardized error responses with a request ID."""

    def __init__(self, request_id: str):
        self._request_id = request_id

    def create_error_response(
        self,
        status_code: int,
        message: str,
        error_code: str | SystemErrorCode | ValidationErrorCode | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Creates a standardized error response."""
        error_body = {
            "message": f"{message}, Request ID: {self._request_id}",
            "request_id": self._request_id,
        }

        if error_code:
            # Convert enum to string if needed
            error_code_str = (
                error_code.value
                if isinstance(error_code, SystemErrorCode | ValidationErrorCode)
                else error_code
            )
            error_body["error_code"] = error_code_str

        if details:
            error_body["details"] = details

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
        rows = cast(list[dict[str, Any]], excel_data.to_dict(orient="records"))
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


def validate_run_type(run_type: str, error_collector: ValidationErrorCollector) -> None:
    """Validate run_type."""
    if not RunType.has_value(run_type):
        valid_run_types = ", ".join([item.value for item in RunType])
        error_collector.add_error(
            message=f"Invalid run_type: {run_type}",
            error_code=ValidationErrorCode.INVALID_RUN_TYPE,
            details={"provided": run_type, "valid_types": valid_run_types.split(", ")},
        )


def validate_template_variables(
    template_content: str,
    recipient_source: str,
    error_collector: ValidationErrorCollector,
    recipients: list[dict[str, Any]] | None = None,
    rows: list[dict[str, Any]] | None = None,
) -> None:
    """Validate that all required template variables are provided.

    Args:
        template_content: The content of template file.
        recipient_source: The source of recipients (SPREADSHEET or DIRECT).
        error_collector: Error collector to accumulate errors.
        recipients: List of recipients with their template variables (for DIRECT mode).
        rows: List of spreadsheet rows (for SPREADSHEET mode).
    """
    required_variables = extract_template_variables(template_content)
    if not required_variables:
        return

    if recipient_source == RecipientSource.DIRECT.value:
        total_errors = 0
        for recipient in recipients or []:
            template_vars = recipient.get("template_variables", {})
            missing_vars = [
                var for var in required_variables if var not in template_vars
            ]
            if missing_vars:
                total_errors += 1

        if total_errors > 0:
            error_collector.add_error(
                message=f"Found {total_errors} recipient(s) with missing template variables",
                error_code=ValidationErrorCode.MISSING_TEMPLATE_VARIABLES_DIRECT,
                details={
                    "required_variables": required_variables,
                    "missing_count": total_errors,
                },
            )
    else:  # SPREADSHEET mode
        total_errors = 0
        for row in rows or []:
            missing_vars = [var for var in required_variables if var not in row]
            if missing_vars:
                total_errors += 1

        if total_errors > 0:
            error_collector.add_error(
                message=f"Found {total_errors} row(s) with missing template variables",
                error_code=ValidationErrorCode.MISSING_TEMPLATE_VARIABLES_SPREADSHEET,
                details={
                    "required_variables": required_variables,
                    "missing_count": total_errors,
                },
            )


def validate_spreadsheet_mode(
    spreadsheet_file_id: str,
    access_token: str,
    error_collector: ValidationErrorCollector,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[str], int]:
    """Validate spreadsheet mode specific requirements."""
    if not spreadsheet_file_id:
        error_collector.add_error(
            message="Spreadsheet file ID is required for SPREADSHEET recipient source",
            error_code=ValidationErrorCode.MISSING_SPREADSHEET_FILE_ID,
        )
        return None, [], [], 0

    try:
        spreadsheet_info = get_file_info(spreadsheet_file_id, access_token)
        spreadsheet_s3_key = spreadsheet_info["s3_object_key"]
    except Exception as e:
        logger.error("Failed to get spreadsheet info: %s", e)
        error_collector.add_error(
            message="Failed to retrieve spreadsheet file information",
            error_code=ValidationErrorCode.SPREADSHEET_INFO_ERROR,
        )
        return None, [], [], 0

    try:
        rows, columns = read_sheet_data_from_s3(spreadsheet_s3_key)
    except Exception as e:
        logger.error("Failed to read spreadshhet: %s", e)
        error_collector.add_error(
            message="Failed to read spreadsheet file. It may be empty or corrupted.",
            error_code=ValidationErrorCode.INVALID_SPREADSHEET_FILE,
        )
        return None, [], [], 0

    # Check if spreadsheet is empty (no rows)
    if not rows or len(rows) == 0:
        error_collector.add_error(
            message="Spreadsheet is empty. Please add at least one recipient.",
            error_code=ValidationErrorCode.EMPTY_SPREADSHEET,
        )

    # Check if spreadsheet has no columns (no headers)
    if not columns or len(columns) == 0:
        error_collector.add_error(
            message="Spreadsheet has no headers. Please add column headers (at least 'Email').",
            error_code=ValidationErrorCode.MISSING_SPREADSHEET_HEADERS,
        )

    # Validate email format
    invalid_emails = []
    for index, row in enumerate(rows, start=1):
        email = row.get("Email")
        if not email:
            invalid_emails.append(
                {"row": index, "email": None, "reason": "Email is missing"}
            )
        elif not re.match(EMAIL_PATTERN, email):
            invalid_emails.append(
                {"row": index, "email": email, "reason": "Invalid email format"}
            )

    if invalid_emails:
        error_collector.add_error(
            message=f"Found {len(invalid_emails)} invalid or missing email(s) in spreadsheet",
            error_code=ValidationErrorCode.INVALID_EMAIL_FORMAT_SPREADSHEET,
            details={
                "invalid_count": len(invalid_emails),
                "invalid_emails": invalid_emails[:10],  # Limit to first 10
            },
        )

    expected_email_send_count = len([row for row in rows if row.get("Email")])
    return spreadsheet_info, rows, columns, expected_email_send_count


def validate_direct_mode(
    recipients: list[dict[str, Any]], error_collector: ValidationErrorCollector
) -> int:
    """Validate direct mode specific requirements."""
    if not recipients:
        error_collector.add_error(
            message="Recipients list cannot be empty",
            error_code=ValidationErrorCode.EMPTY_RECIPIENTS_LIST,
        )
        return 0

    # Validate email format
    invalid_recipients = [
        {"email": recipient.get("email", ""), "index": idx}
        for idx, recipient in enumerate(recipients, start=1)
        if not re.match(EMAIL_PATTERN, recipient.get("email", ""))
    ]

    if invalid_recipients:
        error_collector.add_error(
            message=f"Found {len(invalid_recipients)} invalid email(s) in recipients list",
            error_code=ValidationErrorCode.INVALID_RECIPIENT_EMAIL_FORMAT,
            details={
                "invalid_count": len(invalid_recipients),
                "invalid_emails": invalid_recipients[:10],  # Limit to first 10
            },
        )

    return len(recipients)


def validate_certificate_requirements(
    is_generate_certificate: bool,
    recipient_source: str,
    recipients: list[dict[str, Any]],
    columns: list[str],
    error_collector: ValidationErrorCollector,
) -> None:
    """Validate certificate generation requirements."""
    if not is_generate_certificate:
        return

    required_fields = ["Name", "Certificate Text"]

    if recipient_source == RecipientSource.DIRECT.value:
        missing_fields_list = []
        for idx, recipient in enumerate(recipients, start=1):
            template_vars = recipient.get("template_variables", {})
            missing_fields = [
                field for field in required_fields if field not in template_vars
            ]
            if missing_fields:
                missing_fields_list.append(
                    {
                        "recipient_index": idx,
                        "email": recipient.get("email", "N/A"),
                        "missing_fields": missing_fields,
                    }
                )

        if missing_fields_list:
            error_collector.add_error(
                message=f"Found {len(missing_fields_list)} recipient(s) missing required certificate fields",
                error_code=ValidationErrorCode.MISSING_CERTIFICATE_FIELDS_DIRECT,
                details={
                    "required_fields": required_fields,
                    "missing_count": len(missing_fields_list),
                    "recipients_with_missing_fields": missing_fields_list[:10],
                },
            )
    else:
        missing_required_columns = [
            col for col in required_fields if col not in columns
        ]
        if missing_required_columns:
            error_collector.add_error(
                message="Spreadsheet is missing required columns for certificate generation",
                error_code=ValidationErrorCode.MISSING_CERTIFICATE_COLUMNS_SPREADSHEET,
                details={
                    "required_columns": required_fields,
                    "missing_columns": missing_required_columns,
                    "spreadsheet_columns": columns,
                },
            )


def validate_email_addresses(
    cc: list[str],
    bcc: list[str],
    reply_to: str,
    error_collector: ValidationErrorCollector,
) -> None:
    """Validate email formats for cc, bcc, and reply_to."""
    # Validate CC emails
    invalid_cc = [email for email in cc if not re.match(EMAIL_PATTERN, email)]
    if invalid_cc:
        error_collector.add_error(
            message="Invalid email format in CC list",
            error_code=ValidationErrorCode.INVALID_CC_EMAIL_FORMAT,
            details={"invalid_emails": invalid_cc},
        )

    # Validate BCC emails
    invalid_bcc = [email for email in bcc if not re.match(EMAIL_PATTERN, email)]
    if invalid_bcc:
        error_collector.add_error(
            message="Invalid email format in BCC list",
            error_code=ValidationErrorCode.INVALID_BCC_EMAIL_FORMAT,
            details={"invalid_emails": invalid_bcc},
        )

    # Validate reply_to
    if not re.match(EMAIL_PATTERN, reply_to):
        error_collector.add_error(
            message="Invalid reply_to email format",
            error_code=ValidationErrorCode.INVALID_REPLY_TO_FORMAT,
            details={"email": reply_to},
        )


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

        # Initialize error collector
        error_collector = ValidationErrorCollector()

        # --- Webhook specific logic ---
        if run_type == RunType.WEBHOOK.value:
            logger.info(
                "Processing WEBHOOK run type with run_id: %s and recipients: %s",
                run_id,
                recipients,
            )

            # Validate WEBHOOK run_type requirements
            if not run_id:
                error_collector.add_error(
                    message="run_id is required for WEBHOOK run_type",
                    error_code=ValidationErrorCode.MISSING_RUN_ID_WEBHOOK,
                )

            if recipient_source != RecipientSource.DIRECT.value:
                error_collector.add_error(
                    message="WEBHOOK run_type only supports DIRECT recipient source",
                    error_code=ValidationErrorCode.INVALID_RECIPIENT_SOURCE_WEBHOOK,
                    details={
                        "provided": recipient_source,
                        "required": RecipientSource.DIRECT.value,
                    },
                )

            # Validate required inputs
            if not subject:
                error_collector.add_error(
                    message="Email subject is required",
                    error_code=ValidationErrorCode.MISSING_SUBJECT,
                )
            if not template_file_id:
                error_collector.add_error(
                    message="Template file ID is required",
                    error_code=ValidationErrorCode.MISSING_TEMPLATE_FILE_ID,
                )

            # Validate run_type
            validate_run_type(run_type, error_collector)

            # Get template info and content if template_file_id is provided
            template_info = None
            template_content = None
            if template_file_id:
                try:
                    template_info = get_file_info(template_file_id, access_token)
                    template_content = get_template(template_info["s3_object_key"])
                except Exception as e:
                    logger.error("Failed to get template: %s", e)
                    error_collector.add_error(
                        message="Failed to retrieve template file",
                        error_code=ValidationErrorCode.TEMPLATE_RETRIEVAL_ERROR,
                    )

            # Validate recipients
            validate_direct_mode(recipients, error_collector)

            # Validate template variables if we have the template
            if template_content:
                validate_template_variables(
                    template_content,
                    RecipientSource.DIRECT.value,
                    error_collector,
                    recipients=recipients,
                )

            # Validate certificate requirements
            validate_certificate_requirements(
                is_generate_certificate,
                RecipientSource.DIRECT.value,
                recipients,
                [],
                error_collector,
            )

            # Validate email addresses
            validate_email_addresses(cc, bcc, reply_to, error_collector)

            # Raise all errors if any were collected
            error_collector.raise_if_has_errors()

            # Prepare message body for SQS
            current_user_info = current_user_util.get_current_user_info()
            sender_id = current_user_info.get("user_id")

            message_body = {
                "run_id": run_id,
                "run_type": RunType.WEBHOOK.value,
                "recipient_source": RecipientSource.DIRECT.value,
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
                if not AUTO_RESUMER_SQS_QUEUE_URL:
                    raise ValueError(
                        "AUTO_RESUMER_SQS_QUEUE_URL environment variable not set."
                    )
                send_message_to_queue(AUTO_RESUMER_SQS_QUEUE_URL, message_body)
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
                error_collector.add_error(
                    message="Email subject is required",
                    error_code=ValidationErrorCode.MISSING_SUBJECT,
                )
            if not template_file_id:
                error_collector.add_error(
                    message="Template file ID is required",
                    error_code=ValidationErrorCode.MISSING_TEMPLATE_FILE_ID,
                )
            if run_id:
                error_collector.add_error(
                    message="run_id should not be provided for non-WEBHOOK run_type",
                    error_code=ValidationErrorCode.UNEXPECTED_RUN_ID,
                    details={"run_type": run_type},
                )

            # Validate run_type
            validate_run_type(run_type, error_collector)

            # Generate a new run_id
            run_id = uuid.uuid4().hex

            # Get template information
            template_info = None
            template_content = None
            if template_file_id:
                try:
                    template_info = get_file_info(template_file_id, access_token)
                    template_content = get_template(template_info["s3_object_key"])
                except Exception as e:
                    logger.error("Failed to get template: %s", e)
                    error_collector.add_error(
                        message="Failed to retrieve template file",
                        error_code=ValidationErrorCode.TEMPLATE_RETRIEVAL_ERROR,
                    )

            # Process based on recipient source
            spreadsheet_info = None
            rows, columns = [], []
            expected_email_send_count = 0

            if recipient_source == RecipientSource.SPREADSHEET.value:
                spreadsheet_info, rows, columns, expected_email_send_count = (
                    validate_spreadsheet_mode(
                        spreadsheet_file_id, access_token, error_collector
                    )
                )
                if template_content:
                    validate_template_variables(
                        template_content, recipient_source, error_collector, rows=rows
                    )
            else:  # DIRECT mode
                expected_email_send_count = validate_direct_mode(
                    recipients, error_collector
                )
                if template_content:
                    validate_template_variables(
                        template_content,
                        recipient_source,
                        error_collector,
                        recipients=recipients,
                    )

            # Validate certificate requirements
            validate_certificate_requirements(
                is_generate_certificate,
                recipient_source,
                recipients,
                columns,
                error_collector,
            )

            # Validate email addresses
            validate_email_addresses(cc, bcc, reply_to, error_collector)

            # Raise all errors if any were collected
            error_collector.raise_if_has_errors()

        # Get current user info
        current_user_info = current_user_util.get_current_user_info()
        sender_id = current_user_info.get("user_id")

        # Prepare common data
        common_data = {
            "recipient_source": recipient_source,
            "run_type": run_type,
            "run_id": run_id,
            "template_file_id": template_file_id,
            "spreadsheet_file_id": (
                spreadsheet_file_id
                if recipient_source == RecipientSource.SPREADSHEET.value
                else None
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
            "recipients": (
                recipients if recipient_source == RecipientSource.DIRECT.value else []
            ),
            "success_email_count": 0,
            "expected_email_send_count": expected_email_send_count,
        }

        # Send message to SQS
        message_body = {**common_data, "access_token": access_token}
        try:
            if not AUTO_RESUMER_SQS_QUEUE_URL:
                raise ValueError(
                    "AUTO_RESUMER_SQS_QUEUE_URL environment variable not set."
                )
            send_message_to_queue(AUTO_RESUMER_SQS_QUEUE_URL, message_body)
            logger.info("Message sent to SQS: %s", message_body)
        except (ClientError, ValueError) as e:
            logger.error("Failed to send message to SQS: %s", e)
            return error_responder.create_error_response(
                500,
                "Failed to queue email request",
                SystemErrorCode.SQS_QUEUE_ERROR,
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

    except ValidationError as e:
        logger.error(
            "Validation error - Request ID: %s, Error code: %s, Message: %s, Details: %s",
            aws_request_id,
            e.error_code,
            e.message,
            e.details,
        )
        return error_responder.create_error_response(
            400, e.message, e.error_code, e.details
        )

    except RequestException as e:
        logger.error("External API error: %s", str(e))
        return error_responder.create_error_response(
            502,
            "Failed to communicate with external service",
            SystemErrorCode.EXTERNAL_API_ERROR,
        )

    except ClientError as e:
        logger.error("AWS service error: %s", str(e))
        return error_responder.create_error_response(
            500,
            "Failed to queue email request",
            SystemErrorCode.SQS_QUEUE_ERROR,
        )

    except Exception as e:
        logger.error(
            "Request ID: %s, Unexpected error: %s",
            aws_request_id,
            str(e),
            exc_info=True,
        )
        return error_responder.create_error_response(
            500,
            "An unexpected error occurred. Please try again later or contact support",
            SystemErrorCode.INTERNAL_SERVER_ERROR,
        )
