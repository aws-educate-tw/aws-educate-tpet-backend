import datetime
import io
import json
import logging
import os
import re
import uuid

import boto3
import pandas as pd
import requests
from botocore.exceptions import ClientError
from requests.exceptions import RequestException

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
BUCKET_NAME = os.getenv("BUCKET_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT")
FILE_SERVICE_API_BASE_URL = f"https://{ENVIRONMENT}-file-service-internal-api-tpet.awseducate.systems/{ENVIRONMENT}"


# Function to call API to get file information using the file ID
def get_file_info(file_id):
    try:
        api_url = f"{FILE_SERVICE_API_BASE_URL}/files/{file_id}"
        response = requests.get(api_url)
        response.raise_for_status()
        print("test4")
        return response.json()
    except RequestException as e:
        logger.error("Error in get_file_info: %s", e)
        raise


# Function to retrieve the email template from an S3 bucket
def get_template(template_file_s3_key):
    try:
        s3 = boto3.client("s3")
        request = s3.get_object(Bucket=BUCKET_NAME, Key=template_file_s3_key)
        template_content = request["Body"].read().decode("utf-8")
        return template_content
    except Exception as e:
        logger.error("Error in get_template: %s", e)
        raise


# Function to read and parse spreadsheet data from S3
def read_sheet_data_from_s3(spreadsheet_file_s3_key):
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


# Function to validate template placeholders against spreadsheet columns
def validate_template(template_content, columns):
    try:
        placeholders = re.findall(
            r"{{(.*?)}}", template_content
        )  # placeholder format: {{column_name}}
        missing_columns = [
            placeholder for placeholder in placeholders if placeholder not in columns
        ]
        return missing_columns
    except Exception as e:
        logger.error(
            "Error in excel column, can't find the match placeholder in template: %s", e
        )
        raise


# Function to send email using the SES client
def send_email(ses_client, email_title, template_content, row, display_name):
    try:
        template_content = template_content.replace("\r", "")
        template_content = re.sub(r"\{\{(.*?)\}\}", r"{\1}", template_content)
        receiver_email = row.get("Email")
        if not receiver_email:
            logger.warning("Email address not found in row: %s", row)
            return "FAILED"
        try:
            # Ensure all values in row are strings
            formatted_row = {k: str(v) for k, v in row.items()}
            formatted_content = template_content.format(**formatted_row)
            source_email = "awseducate.cloudambassador@gmail.com"
            formatted_source_email = f"{display_name} <{source_email}>"
            ses_client.send_email(
                Source=formatted_source_email,
                Destination={"ToAddresses": [receiver_email]},
                Message={
                    "Subject": {"Data": email_title},
                    "Body": {"Html": {"Data": formatted_content}},
                },
            )
            _ = datetime.datetime.now() + datetime.timedelta(hours=8)
            formatted_send_time = _.strftime(TIME_FORMAT + "Z")
            logger.info(
                "Email sent to {row.get('Name', 'Unknown')} at %s", formatted_send_time
            )
            return formatted_send_time, "SUCCESS"
        except Exception as e:
            logger.error("Failed to send email to %s: %s", receiver_email, e)
            return None, "FAILED"
    except Exception as e:
        logger.error("Error in send_email: %s", e)
        raise


# Function to save email sending records to DynamoDB
def save_to_dynamodb(
    run_id,
    email_id,
    display_name,
    status,
    recipient_email,
    template_file_id,
    spreadsheet_file_id,
    created_at,
):
    try:
        dynamodb = boto3.resource("dynamodb")
        table_name = os.environ.get("DYNAMODB_TABLE")
        table = dynamodb.Table(table_name)
        item = {
            "run_id": run_id,
            "email_id": email_id,
            "display_name": display_name,
            "status": status,
            "recipient_email": recipient_email,
            "template_file_id": template_file_id,
            "spreadsheet_file_id": spreadsheet_file_id,
            "created_at": created_at,
        }
        table.put_item(Item=item)
    except ClientError as e:
        logger.error("Error in save_to_dynamodb: %s", e)
    except Exception as e:
        logger.error("Error in save_to_dynamodb: %s", e)
        raise


# Function to handle sending emails and saving results to DynamoDB
def process_email(
    ses_client,
    email_title,
    template_content,
    row,
    display_name,
    run_id,
    template_file_id,
    spreadsheet_id,
):
    email = str(row.get("Email", ""))
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        logger.warning("Invalid email address provided: %s", email)
        return "FAILED", email
    send_time, status = send_email(
        ses_client, email_title, template_content, row, display_name
    )
    save_to_dynamodb(
        run_id,
        uuid.uuid4().hex,
        display_name,
        status,
        email,
        template_file_id,
        spreadsheet_id,
        send_time,
    )
    return status, email


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        template_file_id = body.get("template_file_id")
        spreadsheet_id = body.get("spreadsheet_file_id")
        email_title = body.get("subject")
        display_name = body.get("display_name", "No Name Provided")
        run_id = body.get("run_id") if body.get("run_id") else uuid.uuid4().hex

        # Check for missing required parameters
        if not email_title:
            logger.error("Error: Missing required parameter: email_title (subject).")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    "Error: Missing required parameter: email_title (subject)."
                ),
            }
        if not template_file_id:
            logger.error("Error: Missing required parameter: template_file_id.")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    "Error: Missing required parameter: template_file_id."
                ),
            }
        if not spreadsheet_id:
            logger.error("Error: Missing required parameter: spreadsheet_file_id.")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    "Error: Missing required parameter: spreadsheet_file_id."
                ),
            }

        # Fetch and validate template content
        template_info = get_file_info(template_file_id)
        template_s3_key = template_info["s3_object_key"]
        template_content = get_template(template_s3_key)

        # Fetch and read spreadsheet data
        spreadsheet_info = get_file_info(spreadsheet_id)
        spreadsheet_s3_key = spreadsheet_info["s3_object_key"]
        data, columns = read_sheet_data_from_s3(spreadsheet_s3_key)

        # Validate template against spreadsheet columns
        missing_columns = validate_template(template_content, columns)
        if missing_columns:
            error_message = (
                "Template validation error: Missing required columns for placeholders: %s"
                % ", ".join(missing_columns)
            )
            logger.error(error_message)
            return {"statusCode": 400, "body": json.dumps(error_message)}

        # Send emails and save results to DynamoDB
        ses_client = boto3.client("ses", region_name="ap-northeast-1")
        failed_recipients = []
        success_recipients = []
        for row in data:
            status, email = process_email(
                ses_client,
                email_title,
                template_content,
                row,
                display_name,
                run_id,
                template_file_id,
                spreadsheet_id,
            )
            if status == "FAILED":
                failed_recipients.append(email)
            else:
                success_recipients.append(email)

        # Return final response
        if failed_recipients:
            response = {
                "status": "FAILED",
                "message": f"Failed to send {len(failed_recipients)} emails, successfully sent {len(success_recipients)} emails.",
                "failed_recipients": failed_recipients,
                "success_recipients": success_recipients,
                "request_id": run_id,
                "timestamp": datetime.datetime.now().strftime(TIME_FORMAT + "Z"),
                "sqs_message_id": uuid.uuid4().hex,
            }
            logger.info("Response: %s", response)
            return {"statusCode": 500, "body": json.dumps(response)}

        response = {
            "status": "SUCCESS",
            "message": f"All {len(success_recipients)} emails were sent successfully.",
            "request_id": run_id,
            "timestamp": datetime.datetime.now().strftime(TIME_FORMAT + "Z"),
            "sqs_message_id": uuid.uuid4().hex,
        }
        logger.info("Response: %s", response)
        return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as e:
        logger.error("Internal server error: %s", e)
        return {
            "statusCode": 500,
            "body": json.dumps("Internal server error: Detailed error message: %s" % e),
        }
