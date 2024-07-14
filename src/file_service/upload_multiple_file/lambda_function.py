import base64
import json
import logging
import os
import uuid
from urllib.parse import quote, unquote

import boto3
import time_util
from botocore.exceptions import ClientError
from dynamodb import save_to_dynamodb
from requests_toolbelt.multipart import decoder

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize S3 client and DynamoDB client
s3_client = boto3.client("s3")
dynamodb = boto3.client("dynamodb")
BUCKET_NAME = os.environ["BUCKET_NAME"]
S3_BASE_URL = f"https://{BUCKET_NAME}.s3.amazonaws.com/"


def decode_request_body(event):
    """Decode the request body if it's base64 encoded."""
    if event.get("isBase64Encoded", False):
        body = base64.b64decode(event["body"])
    else:
        body = event["body"]
    logger.info("Decoded request body: %s", body)
    return body


def process_files(multipart_data):
    """Process each file in the multipart data."""
    files_metadata = []
    for part in multipart_data.parts:
        try:
            file_metadata = process_single_file(part)
            files_metadata.append(file_metadata)
        except ClientError as e:
            logger.error(
                "Amazon S3 ClientError (%s): %s",
                e.response["Error"]["Code"],
                e.response["Error"]["Message"],
            )
        except Exception as e:
            logger.error("Unknown error: %s", str(e))
    return files_metadata


def process_single_file(part):
    """Process a single file from multipart data."""
    file_name = extract_filename(part)
    content_type = part.headers.get(
        b"Content-Type", b"application/octet-stream"
    ).decode()
    file_content = part.content

    file_id = uuid.uuid4().hex
    unique_file_name = f"{file_id}_{file_name}"

    # Upload file to S3
    logger.info("Uploading file to S3: %s", unique_file_name)
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=unique_file_name,
        Body=file_content,
        ContentType=content_type,
    )
    logger.info("File uploaded successfully: %s", unique_file_name)

    # Generate S3 URL
    encoded_file_name = quote(unique_file_name)
    res_url = S3_BASE_URL + encoded_file_name
    logger.info("Generated S3 URL: %s", res_url)

    # Save metadata to DynamoDB
    file_size = len(file_content)
    save_file_metadata_to_dynamodb(
        file_id, unique_file_name, res_url, file_name, file_size
    )

    return create_file_metadata_dict(
        file_id, unique_file_name, res_url, file_name, file_size
    )


def extract_filename(part):
    """Extract filename from Content-Disposition header."""
    disposition = part.headers[b"Content-Disposition"].decode()
    if "filename*=" in disposition:
        file_name = disposition.split("filename*=UTF-8''")[1]
        return unquote(file_name)
    else:
        return disposition.split('filename="')[1].split('"')[0]


def save_file_metadata_to_dynamodb(
    file_id, unique_file_name, res_url, file_name, file_size
):
    """Save file metadata to DynamoDB."""
    logger.info("Storing file metadata in DynamoDB: %s", file_id)
    save_to_dynamodb(
        file_id=file_id,
        s3_object_key=unique_file_name,
        file_url=res_url,
        file_name=file_name,
        file_size=file_size,
        uploader_id="dummy_uploader_id",  # Replace with actual uploader ID if available
    )
    logger.info("File metadata stored successfully in DynamoDB: %s", file_id)


def create_file_metadata_dict(file_id, unique_file_name, res_url, file_name, file_size):
    """Create a dictionary with file metadata."""
    formatted_now = time_util.get_current_utc_time()
    return {
        "file_id": file_id,
        "s3_object_key": unique_file_name,
        "created_at": formatted_now,
        "updated_at": formatted_now,
        "file_url": res_url,
        "file_name": file_name,
        "file_extension": file_name.split(".")[-1],
        "file_size": file_size,
        "uploader_id": "dummy_uploader_id",  # Replace with actual uploader ID if available
    }


def lambda_handler(event, context):
    """
    Main Lambda function handler for processing file uploads.

    :param event: The event dict containing the API request details
    :param context: The context object providing runtime information
    :return: A dict containing the API response
    """
    logger.info("Received event: %s", event)

    content_type = event["headers"].get("Content-Type") or event["headers"].get(
        "content-type"
    )
    body = decode_request_body(event)

    multipart_data = decoder.MultipartDecoder(body, content_type)
    files_metadata = process_files(multipart_data)

    return {
        "statusCode": 200,
        "body": json.dumps({"files": files_metadata}),
        "headers": {"Content-Type": "application/json"},
    }
