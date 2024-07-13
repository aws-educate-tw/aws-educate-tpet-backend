import io
import json
import logging
import os
import re
import uuid

import boto3
import pandas as pd
import requests
from requests.exceptions import RequestException

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Constants
BUCKET_NAME = os.getenv("BUCKET_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT")
FILE_SERVICE_API_BASE_URL = f"https://{ENVIRONMENT}-file-service-internal-api-tpet.awseducate.systems/{ENVIRONMENT}"
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")


# Initialize AWS SQS client
sqs_client = boto3.client("sqs")


def get_file_info(file_id):
    """
    Retrieve file information from the file service API.

    :param file_id: ID of the file to retrieve information for
    :return: JSON response containing file information
    """
    try:
        api_url = f"{FILE_SERVICE_API_BASE_URL}/files/{file_id}"
        response = requests.get(url=api_url, timeout=25)
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
        # Parse input from the event body
        body = json.loads(event.get("body", "{}"))
        template_file_id = body.get("template_file_id")
        spreadsheet_file_id = body.get("spreadsheet_file_id")
        subject = body.get("subject")
        display_name = body.get("display_name", "No Name Provided")
        run_id = body.get("run_id") if body.get("run_id") else uuid.uuid4().hex
        attachment_file_ids = body.get("attachment_file_ids", [])
        is_generate_certificate = body.get("is_generate_certificate", False)

        # Validate required inputs
        if not subject:
            return {"statusCode": 400, "body": json.dumps("Missing email title")}
        if not template_file_id:
            return {"statusCode": 400, "body": json.dumps("Missing template file ID")}
        if not spreadsheet_file_id:
            return {
                "statusCode": 400,
                "body": json.dumps("Missing spreadsheet file ID"),
            }

        # Get template file information and content
        template_info = get_file_info(template_file_id)
        template_s3_key = template_info["s3_object_key"]
        template_content = get_template(template_s3_key)

        # Get spreadsheet file information and columns
        spreadsheet_info = get_file_info(spreadsheet_file_id)
        spreadsheet_s3_key = spreadsheet_info["s3_object_key"]
        _, columns = read_sheet_data_from_s3(spreadsheet_s3_key)

        # Validate template placeholders against spreadsheet columns
        missing_columns = validate_template(template_content, columns)
        if missing_columns:
            error_message = "Missing required columns for placeholders: %s" % ", ".join(
                missing_columns
            )
            return {"statusCode": 400, "body": json.dumps(error_message)}

        # Validate required columns for certificate generation
        if is_generate_certificate:
            required_columns = ["Name", "Certificate Text"]
            missing_required_columns = [
                col for col in required_columns if col not in columns
            ]
            if missing_required_columns:
                error_message = (
                    "Missing required columns for certificate generation: %s"
                    % ", ".join(missing_required_columns)
                )
                return {"statusCode": 400, "body": json.dumps(error_message)}

        # Prepare message for SQS
        message_body = {
            "run_id": run_id,
            "template_file_id": template_file_id,
            "spreadsheet_file_id": spreadsheet_file_id,
            "subject": subject,
            "display_name": display_name,
            "attachment_file_ids": attachment_file_ids,
            "is_generate_certificate": is_generate_certificate,
        }

        # Send message to SQS
        sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(message_body)
        )
        logger.info("Message sent to SQS: %s", message_body)

        # Prepare success response
        response = {
            "status": "SUCCESS",
            "message": "Input message accepted for processing",
            "run_id": run_id,
            "template_file_id": template_file_id,
            "spreadsheet_file_id": spreadsheet_file_id,
            "subject": subject,
            "display_name": display_name,
            "attachment_file_ids": attachment_file_ids,
            "is_generate_certificate": is_generate_certificate,
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
