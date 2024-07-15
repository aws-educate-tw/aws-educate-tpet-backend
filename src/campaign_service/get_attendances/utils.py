import datetime
import io
import logging
import os
import re
import uuid

import pandas as pd
import requests
from botocore.exceptions import ClientError
from dynamodb import DynamoDB
from s3 import S3
from ses import SES

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
BUCKET_NAME = "aws_educate_tpet_storage"

def get_file_info(file_id):
    try:
        api_url = f"https://api.tpet.awseducate.systems/dev/files/{file_id}"
        response = requests.get(api_url)
        response.raise_for_status()
        logger.info("Fetched file info for file_id: %s", file_id)
        return response.json()
    except Exception as e:
        logger.error("Error in get_file_info: %s", e)
        raise


def get_template(template_file_s3_key):
    try:
        s3 = S3()
        request = s3.get_object(BUCKET_NAME, template_file_s3_key)
        template_content = request["Body"].read().decode("utf-8")
        logger.info("Fetched template content from S3 key: %s", template_file_s3_key)
        return template_content
    except Exception as e:
        logger.error("Error in get_template: %s", e)
        raise


def read_sheet_data_from_s3(spreadsheet_file_s3_key):
    try:
        s3 = S3()
        request = s3.get_object(BUCKET_NAME, spreadsheet_file_s3_key)
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


def send_email(email_title, template_content, row, display_name):
    try:
        ses = SES()
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
            ses.send_email(
                formatted_source_email=formatted_source_email,
                receiver_email=receiver_email,
                email_title=email_title,
                formatted_content=formatted_content,
            )
            _ = datetime.datetime.now() + datetime.timedelta(hours=8)
            formatted_send_time = _.strftime(TIME_FORMAT + "Z")
            logger.info("Email sent to %s at %s", row.get('Name', 'Unknown'), formatted_send_time)
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
        dynamodb = DynamoDB()
        table_name = "campaign"
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
        dynamodb.put_item(table_name=table_name, item=item)
    except ClientError as e:
        logger.error("Error in save_to_dynamodb: %s", e)
    except Exception as e:
        logger.error("Error in save_to_dynamodb: %s", e)
        raise


def process_email(
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
        email_title, template_content, row, display_name
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