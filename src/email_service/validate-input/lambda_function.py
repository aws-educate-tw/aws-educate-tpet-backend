import json
import logging
import os
import re
import boto3
import pandas as pd
import requests
from botocore.exceptions import ClientError
from requests.exceptions import RequestException
import uuid
import io

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BUCKET_NAME = os.environ["BUCKET_NAME"]

sqs_client = boto3.client("sqs")

def get_file_info(file_id):
    try:
        # ! Update the API URL
        api_url = f"https://api.tpet.awseducate.systems/dev/files/{file_id}"
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        logger.error("Error in get_file_info: %s", e)
        raise

def get_template(template_file_s3_key):
    try:
        s3 = boto3.client("s3")
        request = s3.get_object(Bucket=BUCKET_NAME, Key=template_file_s3_key)
        template_content = request["Body"].read().decode("utf-8")
        return template_content
    except Exception as e:
        logger.error("Error in get_template: %s", e)
        raise

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

def validate_template(template_content, columns):
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
    try:
        body = json.loads(event.get("body", "{}"))
        template_file_id = body.get("template_file_id")
        spreadsheet_id = body.get("spreadsheet_file_id")
        email_title = body.get("subject")
        display_name = body.get("display_name", "No Name Provided")
        run_id = body.get("run_id") if body.get("run_id") else uuid.uuid4().hex

        if not email_title:
            return {"statusCode": 400, "body": json.dumps("Missing email title")}
        if not template_file_id:
            return {"statusCode": 400, "body": json.dumps("Missing template file ID")}
        if not spreadsheet_id:
            return {"statusCode": 400, "body": json.dumps("Missing spreadsheet file ID")}

        template_info = get_file_info(template_file_id)
        template_s3_key = template_info["s3_object_key"]
        template_content = get_template(template_s3_key)

        spreadsheet_info = get_file_info(spreadsheet_id)
        spreadsheet_s3_key = spreadsheet_info["s3_object_key"]
        _, columns = read_sheet_data_from_s3(spreadsheet_s3_key)

        missing_columns = validate_template(template_content, columns)
        if missing_columns:
            error_message = "Missing required columns for placeholders: %s" % ", ".join(missing_columns)
            return {"statusCode": 400, "body": json.dumps(error_message)}

        message_body = {
            "run_id": run_id,
            "template_file_id": template_file_id,
            "spreadsheet_file_id": spreadsheet_id,
            "email_title": email_title,
            "display_name": display_name
        }

        sqs_client.send_message(
            QueueUrl=os.environ['SQS_QUEUE_URL'],
            MessageBody=json.dumps(message_body)
        )
        logger.info("Message sent to SQS: %s", message_body)
        response = {
            "status": "SUCCESS",
            "message": "Input message accepted for processing",
            "run_id": run_id,
            "template_file_id": template_file_id,
            "spreadsheet_file_id": spreadsheet_id,
            "email_title": email_title,
            "display_name": display_name
        }
    
        return {"statusCode": 202, "body": json.dumps(response)}

    except Exception as e:
        
        response = {
            "status": "FAILED",
            "message": "Internal server error",
            "error": str(e)
        }
        logger.error("Internal server error: %s", e)
        return {"statusCode": 500, "body": json.dumps(response)}
