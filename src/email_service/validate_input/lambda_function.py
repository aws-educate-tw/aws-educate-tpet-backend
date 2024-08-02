import io
import json
import logging
import os
import re
import uuid

import boto3
import pandas as pd
import requests
from current_user_util import current_user_util  # Import the global instance
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

# Initialize AWS SQS client
sqs_client = boto3.client("sqs")

# Initialize RunRepository
run_repository = RunRepository()


def get_file_info(file_id, access_token):
    """
    Retrieve file information from the file service API.

    :param file_id: ID of the file to retrieve information for
    :param access_token: JWT token for authorization
    :return: JSON response containing file information
    """
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


def get_template(template_file_s3_key):
    """
    Retrieve template content from S3 bucket.

    :param template_file_s3_key: S3 key of the template file
    :return: Decoded content of the template file
    """
    try:
        s3 = boto3.client("s3")
        request = s3.get_object(Bucket=BUCKET_NAME, Key=template_file_s3_key)
        template_content = request["Body"].read().decode("utf-8")
        return template_content
    except Exception as e:
        logger.error("Error in get_template: %s", e)
        raise


def read_sheet_data_from_s3(spreadsheet_file_s3_key):
    """
    Read Excel sheet data from S3 bucket.

    :param spreadsheet_file_s3_key: S3 key of the spreadsheet file
    :return: Tuple containing list of rows and list of column names
    """
    try:
        s3 = boto3.client("s3")
        request = s3.get_object(Bucket=BUCKET_NAME, Key=spreadsheet_file_s3_key)
        xlsx_content = request["Body"].read()
        excel_data = pd.read_excel(io.BytesIO(xlsx_content), engine="openpyxl")
        rows = excel_data.to_dict(orient="records")
        if excel_data.empty:
            return [], 0
        return rows, excel_data.columns.tolist()
    except Exception as e:
        logger.error("Error in read excel from s3: %s", e)
        raise


def validate_template(template_content, columns):
    """
    Validate template placeholders against available columns.

    :param template_content: Content of the template
    :param columns: List of available columns
    :return: List of missing columns
    """
    try:
        placeholders = re.findall(r"{{(.*?)}}", template_content)
        missing_columns = [
            placeholder for placeholder in placeholders if placeholder not in columns
        ]
        return missing_columns
    except Exception as e:
        logger.error("Error in validate_template: %s", e)
        raise


def lambda_handler(event, context):
    """
    Main Lambda function handler.

    :param event: Lambda event object
    :param context: Lambda context object
    :return: Dictionary containing status code and response body
    """
    try:
        # Extract access token from the event headers
        authorization_header = event["headers"].get("authorization")
        if not authorization_header or not authorization_header.startswith("Bearer "):
            return {
                "statusCode": 401,
                "body": json.dumps(
                    {"message": "Missing or invalid Authorization header"}
                ),
                "headers": {"Content-Type": "application/json"},
            }

        access_token = authorization_header.split(" ")[1]

        # Set the current user information using the access token
        current_user_util.set_current_user_by_access_token(access_token)

        # Parse input from the event body
        body = json.loads(event.get("body", "{}"))
        template_file_id = body.get("template_file_id")
        spreadsheet_file_id = body.get("spreadsheet_file_id")
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
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing email title"}),
            }
        if not template_file_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing template file ID"}),
            }
        if not spreadsheet_file_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing spreadsheet file ID"}),
            }

        # Validate email formats
        email_pattern = r"[^@]+@[^@]+\.[^@]+"
        for email_list in [cc, bcc]:
            for email in email_list:
                if not re.match(email_pattern, email):
                    return {
                        "statusCode": 400,
                        "body": json.dumps(
                            {"message": f"Invalid email format: {email}"}
                        ),
                    }

        if not re.match(email_pattern, reply_to):
            return {
                "statusCode": 400,
                "body": json.dumps({"message": f"Invalid email format: {reply_to}"}),
            }

        current_user_info = current_user_util.get_current_user_info()
        sender_id = current_user_info.get("user_id")

        # Get template file information and content
        template_info = get_file_info(template_file_id, access_token)
        template_s3_key = template_info["s3_object_key"]
        template_content = get_template(template_s3_key)

        # Get spreadsheet file information and columns
        spreadsheet_info = get_file_info(spreadsheet_file_id, access_token)
        spreadsheet_s3_key = spreadsheet_info["s3_object_key"]
        rows, columns = read_sheet_data_from_s3(spreadsheet_s3_key)

        # Validate template placeholders against spreadsheet columns
        missing_columns = validate_template(template_content, columns)
        if missing_columns:
            error_message = f"Missing required columns for placeholders: {', '.join(missing_columns)}"
            return {"statusCode": 400, "body": json.dumps({"message": error_message})}

        # Validate required columns for certificate generation
        if is_generate_certificate:
            required_columns = ["Name", "Certificate Text"]
            missing_required_columns = [
                col for col in required_columns if col not in columns
            ]
            if missing_required_columns:
                error_message = f"Missing required columns for certificate generation: {', '.join(missing_required_columns)}"
                return {
                    "statusCode": 400,
                    "body": json.dumps({"message": error_message}),
                }

        # Validate emails in spreadsheet
        invalid_emails = []
        for index, row in enumerate(rows, start=1):
            email = row.get("Email")
            if not email or pd.isna(email) or not re.match(email_pattern, email):
                invalid_emails.append({"row": index, "email": email})

        if invalid_emails:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"message": f"Invalid email(s) in spreadsheet: {invalid_emails}"}
                ),
            }

        # Calculate the number of emails to be sent
        expected_email_send_count = len([row for row in rows if row.get("Email")])

        # Get attachment file information if any
        attachment_files = []
        for file_id in attachment_file_ids:
            attachment_info = get_file_info(file_id, access_token)
            attachment_files.append(attachment_info)

        # Prepare common data for message and response
        common_data = {
            "run_id": run_id,
            "template_file_id": template_file_id,
            "spreadsheet_file_id": spreadsheet_file_id,
            "subject": subject,
            "display_name": display_name,
            "attachment_file_ids": attachment_file_ids,
            "is_generate_certificate": is_generate_certificate,
            "sender_id": sender_id,
            "reply_to": reply_to,
            "sender_local_part": sender_local_part,
            "cc": cc,
            "bcc": bcc,
            "expected_email_send_count": expected_email_send_count,
        }

        # Get current time and extract date parts
        created_at = get_current_utc_time()
        created_year = created_at[:4]
        created_year_month = created_at[:7]
        created_year_month_day = created_at[:10]

        # Save run item to DynamoDB
        run_item = {
            **common_data,
            "created_at": created_at,
            "created_year": created_year,
            "created_year_month": created_year_month,
            "created_year_month_day": created_year_month_day,
            "template_file": template_info,
            "spreadsheet_file": spreadsheet_info,
            "attachment_files": attachment_files,
            "sender": current_user_info,
        }

        # Convert floats to decimals
        run_item = convert_float_to_decimal(run_item)

        saved_run_id = run_repository.save_run(run_item)
        if not saved_run_id:
            return {
                "statusCode": 500,
                "body": json.dumps({"message": "Failed to save run"}),
            }

        # Prepare message for SQS
        message_body = {
            **common_data,
            "access_token": access_token,
        }

        # Send message to SQS
        sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(message_body)
        )
        logger.info("Message sent to SQS: %s", message_body)

        # Prepare success response
        response = {
            "status": "SUCCESS",
            "message": "Your send email request has been successfully received and is being processed.",
            **common_data,
        }

        return {"statusCode": 202, "body": json.dumps(response)}

    except Exception as e:
        # Handle exceptions and return error response
        response = {
            "status": "FAILED",
            "message": "Internal server error",
            "error": str(e),
        }
        logger.error("Internal server error: %s", e)
        return {"statusCode": 500, "body": json.dumps(response)}
