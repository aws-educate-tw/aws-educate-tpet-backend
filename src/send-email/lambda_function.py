import re
import datetime
import io
import json
import os
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from requests.exceptions import RequestException
import pandas as pd
import uuid
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Function to call API to get file information using the file ID
def get_file_info(file_id):
    try:
        api_url = f"https://8um2zizr80.execute-api.ap-northeast-1.amazonaws.com/dev/files/{file_id}"
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        logger.error(f"Error in get_file_info: {str(e)}")
        raise

# Function to retrieve the email template from an S3 bucket
def get_template(template_file_s3_key):
    try:
        s3 = boto3.client("s3")
        bucket_name = os.environ.get("BUCKET_NAME")
        request = s3.get_object(Bucket=bucket_name, Key=template_file_s3_key)
        template_content = request['Body'].read().decode("utf-8")
        return template_content
    except Exception as e:
        logger.error(f"Error in get_template: {str(e)}")
        raise

# Function to read and parse spreadsheet data from S3
def read_sheet_data_from_s3(spreadsheet_file_s3_key):
    try:
        s3 = boto3.client("s3")
        bucket_name = os.environ.get("BUCKET_NAME")
        request = s3.get_object(Bucket=bucket_name, Key=spreadsheet_file_s3_key)
        xlsx_content = request['Body'].read()
        excel_data = pd.read_excel(io.BytesIO(xlsx_content), engine='openpyxl')
        rows = excel_data.to_dict(orient='records')
        if excel_data.empty:
            return [], 0, True
        return rows, excel_data.columns.tolist()
    except Exception as e:
        logger.error(f"Error in read excel from s3: {str(e)}")
        raise

# Function to validate template placeholders against spreadsheet columns
def validate_template(template_content, columns):
    try:
        placeholders = re.findall(r'{{(.*?)}}', template_content) # placeholder format: {{column_name}}
        missing_columns = [placeholder for placeholder in placeholders if placeholder not in columns]
        return missing_columns
    except Exception as e:
        logger.error(f"Error in excel column, can't find the match placeholder in template: {str(e)}")
        raise

# Function to send email using the SES client
def send_email(ses_client, email_title, template_content, row, display_name):
    try:
        template_content = template_content.replace("\r", "")
        template_content = re.sub(r'\{\{(.*?)\}\}', r'{\1}', template_content)
        receiver_email = row.get("Email")
        if not receiver_email:
            logger.warning(f"No email address provided for {row.get('Name', 'Unknown')}. Skipping...")
            return "Failed", "FAILED"
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
                    "Body": {"Html": {"Data": formatted_content}}
                }
            )
            _ = datetime.datetime.now() + datetime.timedelta(hours=8)
            formatted_send_time = _.strftime(TIME_FORMAT)
            logger.info(f"Email sent to {row.get('Name', 'Unknown')} at {formatted_send_time}")
            return formatted_send_time, "SUCCESS"
        except Exception as e:
            logger.error(f"Failed to send email to {row.get('Name', 'Unknown')}: {e}")
            return "Failed", "FAILED"
    except Exception as e:
        logger.error(f"Error in send_email: {str(e)}")
        raise

# Function to save email sending records to DynamoDB
def save_to_dynamodb(run_id, email_id, display_name, status, recipient_email, template_file_id, spreadsheet_file_id, created_at):
    try:
        dynamodb = boto3.resource('dynamodb')
        table_name = os.environ.get('DYNAMODB_TABLE')
        table = dynamodb.Table(table_name)
        item = {
            'run_id': run_id,
            'email_id': email_id,
            'display_name': display_name,
            'status': status,
            'recipient_email': recipient_email,
            'template_file_id': template_file_id,
            'spreadsheet_file_id': spreadsheet_file_id,
            'created_at': created_at
        }   
        table.put_item(Item=item)
    except ClientError as e:
        logger.error(f"Error saving to DynamoDB: {e}")
    except Exception as e:
        logger.error(f"Error in save_to_dynamodb: {str(e)}")
        raise

# Function to handle sending emails and saving results to DynamoDB
def process_email(ses_client, email_title, template_content, row, display_name, run_id, template_file_id, spreadsheet_id):
    email = str(row.get("Email", ""))
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        logger.warning(f"Invalid email format: {email}. Skipping...") # If email is invalid, skip sending
        return "FAILED", email
    send_time, status = send_email(ses_client, email_title, template_content, row, display_name)
    save_to_dynamodb(run_id, uuid.uuid4().hex, display_name, status, email, template_file_id, spreadsheet_id, send_time)
    return status, email

# Main lambda handler function
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
            return {"statusCode": 400, "body": json.dumps("Error: Missing required parameter: email_title (subject).")}
        if not template_file_id:
            logger.error("Error: Missing required parameter: template_file_id.")
            return {"statusCode": 400, "body": json.dumps("Error: Missing required parameter: template_file_id.")}
        if not spreadsheet_id:
            logger.error("Error: Missing required parameter: spreadsheet_file_id.")
            return {"statusCode": 400, "body": json.dumps("Error: Missing required parameter: spreadsheet_file_id.")}

        # Fetch and validate template content
        try:
            template_info = get_file_info(template_file_id)
            template_s3_key = template_info["s3_object_key"]
            template_content = get_template(template_s3_key)
        except Exception as e:
            logger.error(f"Error fetching or reading template: {str(e)}")
            return {"statusCode": 502, "body": json.dumps(f"Error fetching or reading template: {str(e)}")}

        # Fetch and read spreadsheet data
        try:
            spreadsheet_info = get_file_info(spreadsheet_id)
            spreadsheet_s3_key = spreadsheet_info["s3_object_key"]
            data, columns = read_sheet_data_from_s3(spreadsheet_s3_key)
        except Exception as e:
            logger.error(f"Error fetching or reading spreadsheet: {str(e)}")
            return {"statusCode": 502, "body": json.dumps(f"Error fetching or reading spreadsheet: {str(e)}")}

        # Validate template against spreadsheet columns
        missing_columns = validate_template(template_content, columns)
        if (missing_columns):
            logger.error(f"Template validation error: Missing required columns for placeholders: {', '.join(missing_columns)}")
            return {"statusCode": 400, "body": json.dumps(f"Template validation error: Missing required columns for placeholders: {', '.join(missing_columns)}")}

        # Send emails and save results to DynamoDB
        ses_client = boto3.client("ses", region_name="ap-northeast-1")
        failed_recipients = []
        success_recipients = []
        for row in data:
            status, email = process_email(ses_client, email_title, template_content, row, display_name, run_id, template_file_id, spreadsheet_id)
            if status == "FAILED":
                failed_recipients.append(email)
            else:
                success_recipients.append(email)

        # Return final response
        if failed_recipients:
            response = {
                "status": "failed",
                "message": f"Failed to send {len(failed_recipients)} emails, successfully sent {len(success_recipients)} emails.",
                "failed_recipients": failed_recipients,
                "success_recipients": success_recipients,
                "request_id": run_id,
                "timestamp": datetime.datetime.now().strftime(TIME_FORMAT),
                "sqs_message_id": uuid.uuid4().hex
            }
            logger.info(f"Response: {response}")
            return {"statusCode": 500, "body": json.dumps(response)}
        else:
            response = {
                "status": "success",
                "message": f"All {len(success_recipients)} emails were sent successfully.",
                "request_id": run_id,
                "timestamp": datetime.datetime.now().strftime(TIME_FORMAT),
                "sqs_message_id": uuid.uuid4().hex
            }
            logger.info(f"Response: {response}")
            return {"statusCode": 200, "body": json.dumps(response)}
    except Exception as e:
        logger.error(f"Internal server error: Detailed error message: {str(e)}")
        return {"statusCode": 500, "body": json.dumps(f"Internal server error: Detailed error message: {str(e)}")}
