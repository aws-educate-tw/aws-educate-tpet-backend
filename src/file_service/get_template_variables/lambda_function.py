import json
import logging
import os
import re
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError
from s3 import read_html_template_file_from_s3

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def extract_template_variables(html_content: str) -> list[str]:
    """
    Extract template variables from HTML content using regex.
    Template variables are in the format {{variable_name}}

    Args:
        html_content (str): The HTML content to parse

    Returns:
        list[str]: List of unique variable names found in the content
    """
    try:
        placeholders = re.findall(r"{{(.*?)}}", html_content)

        # Remove duplicates and strip whitespace
        variables = list({placeholder.strip() for placeholder in placeholders})
        
        # Sort for consistent output
        variables.sort()

        return variables
    except Exception as e:
        logger.error("Error in extract_template_variables: %s", e)
        raise


def lambda_handler(event, context):
    """
    Lambda function handler for getting template variables from HTML files.

    Expected path: GET /files/{file_id}/template-variables
    """
    # Handle prewarm requests
    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    try:
        # Extract file_id from path parameters
        file_id = event["pathParameters"]["file_id"]
        logger.info(f"Processing template variables request for file_id: {file_id}")

        # Get file metadata from DynamoDB
        response = table.get_item(Key={"file_id": file_id})

        if "Item" not in response:
            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"message": "File not found"}),
            }

        file_item = response["Item"]

        # Check if file is HTML
        file_extension = file_item.get("file_extension", "").lower()
        if file_extension != "html":
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "message": "Template variable extraction is only supported for HTML files"
                    }
                ),
            }

        # Download file content from S3
        s3_object_key = file_item["s3_object_key"]
        bucket_name = os.getenv("S3_BUCKET_NAME")
        html_content = read_html_template_file_from_s3(bucket_name, s3_object_key)

        # Extract template variables
        variables = extract_template_variables(html_content)

        # Prepare response
        result = {
            "status": "SUCCESS",
            "file_id": file_item["file_id"],
            "s3_object_key": file_item["s3_object_key"],
            "file_url": file_item["file_url"],
            "file_name": file_item["file_name"],
            "file_extension": file_item["file_extension"],
            "variables": variables,
            "variable_count": len(variables),
        }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(result, cls=DecimalEncoder),
        }

    except ClientError as e:
        logger.error(f"AWS service error: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Error accessing AWS services"}),
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"message": "Internal server error"}),
        }
