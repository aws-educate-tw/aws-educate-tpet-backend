import base64
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

import boto3
from botocore.exceptions import ClientError
from requests_toolbelt.multipart import decoder

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client and DynamoDB client
s3_client = boto3.client("s3")
dynamodb = boto3.client("dynamodb")
BUCKET_NAME = os.environ["BUCKET_NAME"]
TABLE_NAME = os.environ["TABLE_NAME"]
S3_BASE_URL = f"https://{BUCKET_NAME}.s3.amazonaws.com/"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


def lambda_handler(event, context):
    logger.info("Received event: %s", event)
    content_type = event["headers"].get("Content-Type") or event["headers"].get(
        "content-type"
    )
    # Check if the body is base64 encoded
    if event.get("isBase64Encoded", False):
        body = base64.b64decode(event["body"])  # Decode base64-encoded body
    else:
        body = event["body"]  # Use the body as is
    logger.info("Decoded request body: %s", body)
    multipart_data = decoder.MultipartDecoder(body, content_type)

    try:
        # Assume only one file in the request
        part = multipart_data.parts[0]
        disposition = part.headers[b"Content-Disposition"].decode()
        if "filename*=" in disposition:
            file_name = disposition.split("filename*=UTF-8''")[1]
        else:
            file_name = disposition.split('filename="')[1].split('"')[0]

        unique_file_name = str(uuid.uuid4()) + "_" + file_name
        content_type = part.headers.get(
            b"Content-Type", b"application/octet-stream"
        ).decode()
        file_content = part.content

        # Upload file to S3
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=unique_file_name,
            Body=file_content,
            ContentType=content_type,
        )

        encoded_file_name = quote(unique_file_name)
        res_url = S3_BASE_URL + encoded_file_name

        # Generate file metadata and store it in DynamoDB
        now = datetime.now(timezone.utc)
        formatted_now = now.strftime(TIME_FORMAT) + "Z"
        file_id = uuid.uuid4().hex
        file_size = len(file_content)

        dynamodb.put_item(
            TableName=TABLE_NAME,
            Item={
                "file_id": {"S": file_id},
                "create_at": {"S": formatted_now},
                "update_at": {"S": formatted_now},
                "file_url": {"S": res_url},
                "file_name": {"S": file_name},
                "file_extension": {"S": file_name.split(".")[-1]},
                "file_size": {"N": str(file_size)},
                "uploader_id": {
                    "S": "dummy_uploader_id"
                },  # Replace with actual uploader ID if available
            },
        )

        # Prepare the response file metadata
        file_metadata = {
            "file_id": file_id,
            "created_at": formatted_now,
            "updated_at": formatted_now,
            "file_url": res_url,
            "file_name": file_name,
            "file_extension": file_name.split(".")[-1],
            "file_size": file_size,
            "uploader_id": "dummy_uploader_id",  # Replace with actual uploader ID if available
        }

        return {
            "statusCode": 200,
            "body": json.dumps(file_metadata),
            "headers": {"Content-Type": "application/json"},
        }

    except ClientError as e:
        print(f"Amazon S3 error: {e.response['Error']['Message']}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": "Amazon S3 error", "message": e.response["Error"]["Message"]}
            ),
            "headers": {"Content-Type": "application/json"},
        }
    except Exception as e:
        print(f"Unknown error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Unknown error", "message": str(e)}),
            "headers": {"Content-Type": "application/json"},
        }
