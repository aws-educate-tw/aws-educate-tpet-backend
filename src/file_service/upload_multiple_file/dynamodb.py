import logging
import os
from typing import Any, Dict

import boto3
import time_util

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.client("dynamodb")
DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]


def save_to_dynamodb(
    file_id: str,
    s3_object_key: str,
    file_url: str,
    file_name: str,
    file_size: int,
    uploader_id: str,
) -> Dict[str, Any]:
    formatted_now = time_util.get_current_utc_time()

    dynamodb.put_item(
        TableName=DYNAMODB_TABLE,
        Item={
            "file_id": {"S": file_id},
            "s3_object_key": {"S": s3_object_key},
            "created_at": {"S": formatted_now},
            "updated_at": {"S": formatted_now},
            "file_url": {"S": file_url},
            "file_name": {"S": file_name},
            "file_extension": {"S": file_name.split(".")[-1]},
            "file_size": {"N": str(file_size)},
            "uploader_id": {
                "S": uploader_id
            },  # Replace with actual uploader ID if available
        },
    )

    return {
        "file_id": file_id,
        "s3_object_key": s3_object_key,
        "created_at": formatted_now,
        "updated_at": formatted_now,
        "file_url": file_url,
        "file_name": file_name,
        "file_extension": file_name.split(".")[-1],
        "file_size": file_size,
        "uploader_id": "dummy_uploader_id",  # Replace with actual uploader ID if available
    }
