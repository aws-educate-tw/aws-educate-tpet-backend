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

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE")
BUCKET_NAME = os.getenv("BUCKET_NAME")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
ENVIRONMENT = os.getenv("ENVIRONMENT")
FILE_SERVICE_API_BASE_URL = f"https://{ENVIRONMENT}-file-service-internal-api-tpet.awseducate.systems/{ENVIRONMENT}"


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
    try:
        s3 = boto3.client("s3")
        request = s3.get_object(Bucket=BUCKET_NAME, Key=template_file_s3_key)
        template_content = request["Body"].read().decode("utf-8")
        logger.info("Fetched template content from S3 key: %s", template_file_s3_key)
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
        logger.info("Read sheet data from S3 key: %s", spreadsheet_file_s3_key)
        return rows, excel_data.columns.tolist()
    except Exception as e:
        logger.error("Error in read excel from s3: %s", e)
        raise


def send_email(ses_client, email_title, template_content, row, display_name):
    try:
        template_content = template_content.replace("\r", "")
        template_content = re.sub(r"\{\{(.*?)\}\}", r"{\1}", template_content)
        receiver_email = row.get("Email")
        if not receiver_email:
            logger.warning("Email address not found in row: %s", row)
            return None, "FAILED"
        try:
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
                "Email sent to %s at %s",
                row.get("Name", "Unknown"),
                formatted_send_time,
            )
            return formatted_send_time, "SUCCESS"
        except Exception as e:
            logger.error("Failed to send email to %s: %s", receiver_email, e)
            return None, "FAILED"
    except Exception as e:
        logger.error("Error in send_email: %s", e)
        return None, "FAILED"


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
        table_name = DYNAMODB_TABLE
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
        logger.info("Saved email record to DynamoDB: %s", email_id)
    except ClientError as e:
        logger.error("Error in save_to_dynamodb: %s", e)
    except Exception as e:
        logger.error("Error in save_to_dynamodb: %s", e)
        raise


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


def delete_sqs_message(sqs_client, queue_url, receipt_handle):
    try:
        sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        logger.info("Deleted message from SQS: %s", receipt_handle)
    except Exception as e:
        logger.error("Error deleting message from SQS: %s", e)
        raise


def lambda_handler(event, context):
    sqs_client = boto3.client("sqs")
    queue_url = SQS_QUEUE_URL

    for record in event["Records"]:
        try:
            body = json.loads(record["body"])
            receipt_handle = record["receiptHandle"]
            template_file_id = body.get("template_file_id")
            spreadsheet_id = body.get("spreadsheet_file_id")
            email_title = body.get("email_title")
            display_name = body.get("display_name")
            run_id = body.get("run_id")

            logger.info("Processing message with run_id: %s", run_id)

            template_info = get_file_info(template_file_id)
            template_s3_key = template_info["s3_object_key"]
            template_content = get_template(template_s3_key)

            spreadsheet_info = get_file_info(spreadsheet_id)
            spreadsheet_s3_key = spreadsheet_info["s3_object_key"]
            data, _ = read_sheet_data_from_s3(spreadsheet_s3_key)

            ses_client = boto3.client("ses", region_name="ap-northeast-1")
            for row in data:
                process_email(
                    ses_client,
                    email_title,
                    template_content,
                    row,
                    display_name,
                    run_id,
                    template_file_id,
                    spreadsheet_id,
                )
            logger.info("Processed all emails for run_id: %s", run_id)
        except Exception as e:
            logger.error("Error processing message: %s", e)
        finally:
            if queue_url:
                try:
                    delete_sqs_message(sqs_client, queue_url, receipt_handle)
                    logger.info("Deleted message from SQS: %s", receipt_handle)
                except Exception as e:
                    logger.error("Error deleting SQS message: %s", e)
            else:
                logger.error("SQS_QUEUE_URL is not available")
