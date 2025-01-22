import json
import logging
import os
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def lambda_handler(event, context):
    # Identify if the incoming event is a prewarm request
    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    file_id = event["pathParameters"]["file_id"]
    print("test")
    response = table.get_item(Key={"file_id": file_id})

    if "Item" not in response:
        return {"statusCode": 404, "body": json.dumps({"message": "File not found"})}

    file_item = response["Item"]

    result = {
        "file_id": file_item["file_id"],
        "s3_object_key": file_item["s3_object_key"],
        "created_at": file_item["created_at"],
        "updated_at": file_item["updated_at"],
        "file_url": file_item["file_url"],
        "file_name": file_item["file_name"],
        "file_extension": file_item["file_extension"],
        "file_size": file_item["file_size"],
        "uploader_id": file_item["uploader_id"],
    }

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(result, cls=DecimalEncoder),
    }
