import base64
import json
import logging
import os
from decimal import Decimal

import boto3
import botocore.exceptions
from boto3.dynamodb.conditions import Key

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def encode_key(key):
    """Encodes a dictionary key to a base64 string."""
    try:
        return base64.b64encode(json.dumps(key).encode('utf-8')).decode('utf-8')
    except (TypeError, ValueError) as e:
        logger.error("Failed to encode key: %s", str(e))
        return None


def decode_key(encoded_key):
    """Decodes a base64 string to a dictionary key."""
    try:
        return json.loads(base64.b64decode(encoded_key).decode('utf-8'))
    except (json.JSONDecodeError, base64.binascii.Error) as e:
        logger.error("Failed to decode key: %s", str(e))
        return None


def lambda_handler(event, context):
    """Lambda function handler for listing runs."""
    # Initialize query parameters with default values
    limit = 10
    last_evaluated_key = None
    first_evaluated_key = None
    sort_by = "created_at"
    sort_order = "DESC"

    # Extract query parameters if they exist
    if event.get("queryStringParameters"):
        limit = int(event["queryStringParameters"].get("limit", 10))
        last_evaluated_key = event["queryStringParameters"].get("last_evaluated_key", None)
        first_evaluated_key = event["queryStringParameters"].get("first_evaluated_key", None)
        sort_by = event["queryStringParameters"].get("sort_by", "created_at")
        sort_order = event["queryStringParameters"].get("sort_order", "DESC")

    # Log the extracted parameters
    logger.info(
        "Extracted parameters - limit: %d, last_evaluated_key: %s, first_evaluated_key: %s, sort_by: %s, sort_order: %s",
        limit,
        last_evaluated_key,
        first_evaluated_key,
        sort_by,
        sort_order,
    )

    scan_kwargs = {
        "Limit": limit,
    }

    if last_evaluated_key:
        last_evaluated_key = decode_key(last_evaluated_key)
        if last_evaluated_key:
            scan_kwargs["ExclusiveStartKey"] = last_evaluated_key
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Invalid last_evaluated_key format. It must be a valid base64 encoded JSON string."
                }),
            }

    # Scan the table using the provided parameters
    try:
        response = table.scan(**scan_kwargs)
        logger.info("Scan successful")
    except botocore.exceptions.ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ValidationException":
            logger.error("Scan failed: %s", str(e))
            return {"statusCode": 400, "body": json.dumps({"error": str(e)})}
        else:
            raise e

    records = response.get("Items", [])
    last_evaluated_key = response.get("LastEvaluatedKey")

    # Set the first_evaluated_key if this is the first page of results
    if not first_evaluated_key and records:
        first_evaluated_key = encode_key(records[0])

    # Sort the results by sort_by
    reverse_order = True if sort_order.upper() == "DESC" else False
    records.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse_order)

    # Encode last_evaluated_key to base64 if it's not null
    if last_evaluated_key:
        last_evaluated_key = encode_key(last_evaluated_key)
        logger.info("Encoded last_evaluated_key: %s", last_evaluated_key)

    result = {
        "data": records,
        "last_evaluated_key": last_evaluated_key if last_evaluated_key else None,
        "first_evaluated_key": first_evaluated_key if first_evaluated_key else None
    }

    logger.info("Returning response with %d records", len(records))
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(result, cls=DecimalEncoder),
    }
