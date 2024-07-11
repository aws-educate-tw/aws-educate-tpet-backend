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
DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]
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

    files_metadata = []

    for part in multipart_data.parts:
        try:
            disposition = part.headers[b"Content-Disposition"].decode()
            if "filename*=" in disposition:
                file_name = disposition.split("filename*=UTF-8''")[1]
            else:
                file_name = disposition.split('filename="')[1].split('"')[0]

            content_type = part.headers.get(
                b"Content-Type", b"application/octet-stream"
            ).decode()
            file_content = part.content

            # Generate file_id without hyphens and use it as the S3 object key
            file_id = uuid.uuid4().hex  # UUID without hyphens
            unique_file_name = file_id + "_" + file_name

            print(f"Uploading file to S3: {unique_file_name}")

            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=unique_file_name,
                Body=file_content,
                ContentType=content_type,
            )

            print(f"File uploaded successfully: {unique_file_name}")

            encoded_file_name = quote(unique_file_name)
            res_url = S3_BASE_URL + encoded_file_name

            print(f"Generated S3 URL: {res_url}")

            # Generate file metadata and store it in DynamoDB
            now = datetime.now(timezone.utc)
            formatted_now = now.strftime(TIME_FORMAT) + "Z"
            file_size = len(file_content)

            print(f"Storing file metadata in DynamoDB: {file_id}")

            dynamodb.put_item(
                TableName=DYNAMODB_TABLE,
                Item={
                    "file_id": {"S": file_id},
                    "s3_object_key": {"S": unique_file_name},
                    "created_at": {"S": formatted_now},
                    "updated_at": {"S": formatted_now},
                    "file_url": {"S": res_url},
                    "file_name": {"S": file_name},
                    "file_extension": {"S": file_name.split(".")[-1]},
                    "file_size": {"N": str(file_size)},
                    "uploader_id": {
                        "S": "dummy_uploader_id"
                    },  # Replace with actual uploader ID if available
                },
            )

            print(f"File metadata stored successfully in DynamoDB: {file_id}")

            # Append file metadata to the response
            files_metadata.append(
                {
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
            )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            print(f"Amazon S3 ClientError ({error_code}): {error_message}")
        except Exception as e:
            print(f"Unknown error: {str(e)}")

    return {
        "statusCode": 200,
        "body": json.dumps({"files": files_metadata}),
        "headers": {"Content-Type": "application/json"},
    }
