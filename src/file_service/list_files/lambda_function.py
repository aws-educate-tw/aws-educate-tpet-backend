import base64
import json
import logging
import os
from decimal import Decimal

import boto3
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


def lambda_handler(event, context):
    """Lambda function handler for listing files."""
    # Initialize query parameters with default values
    limit = 10
    last_evaluated_key = None
    file_extension = None
    sort_order = "DESC"

    # Extract query parameters if they exist
    if event.get("queryStringParameters"):
        limit = int(event["queryStringParameters"].get("limit", 10))
        last_evaluated_key = event["queryStringParameters"].get(
            "last_evaluated_key", None
        )
        sort_order = event["queryStringParameters"].get("sort_order", "DESC")
        file_extension = event["queryStringParameters"].get("file_extension", None)

    # Log the extracted parameters
    logger.info(
        "Extracted parameters - limit: %d, last_evaluated_key: %s, sort_order: %s, file_extension: %s",
        limit,
        last_evaluated_key,
        sort_order,
        file_extension,
    )

    if file_extension:
        query_kwargs = {
            "Limit": limit,
            "IndexName": "file_extension-created_at-gsi",
            "ScanIndexForward": False if sort_order.upper() == "DESC" else True,
            "KeyConditionExpression": Key("file_extension").eq(file_extension),
        }

        if last_evaluated_key:
            try:
                # Decode the base64 last_evaluated_key
                last_evaluated_key = json.loads(
                    base64.b64decode(last_evaluated_key).decode("utf-8")
                )
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key
                logger.info("Decoded last_evaluated_key: %s", last_evaluated_key)
            except (json.JSONDecodeError, base64.binascii.Error) as e:
                logger.error("Invalid last_evaluated_key format: %s", str(e))
                return {
                    "statusCode": 400,
                    "body": json.dumps(
                        {
                            "error": "Invalid last_evaluated_key format. It must be a valid base64 encoded JSON string."
                        }
                    ),
                }

        # Query the table using the provided parameters
        try:
            response = table.query(**query_kwargs)
            logger.info("Query successful")
        except dynamodb.meta.client.exceptions.ValidationException as e:
            logger.error("Query failed: %s", str(e))
            return {"statusCode": 400, "body": json.dumps({"error": str(e)})}
    else:
        scan_kwargs = {
            "Limit": limit,
        }

        if last_evaluated_key:
            try:
                # Decode the base64 last_evaluated_key
                last_evaluated_key = json.loads(
                    base64.b64decode(last_evaluated_key).decode("utf-8")
                )
                scan_kwargs["ExclusiveStartKey"] = last_evaluated_key
                logger.info("Decoded last_evaluated_key: %s", last_evaluated_key)
            except (json.JSONDecodeError, base64.binascii.Error) as e:
                logger.error("Invalid last_evaluated_key format: %s", str(e))
                return {
                    "statusCode": 400,
                    "body": json.dumps(
                        {
                            "error": "Invalid last_evaluated_key format. It must be a valid base64 encoded JSON string."
                        }
                    ),
                }

        # Scan the table using the provided parameters
        try:
            response = table.scan(**scan_kwargs)
            logger.info("Scan successful")
        except dynamodb.meta.client.exceptions.ValidationException as e:
            logger.error("Scan failed: %s", str(e))
            return {"statusCode": 400, "body": json.dumps({"error": str(e)})}

    files = response.get("Items", [])
    last_evaluated_key = response.get("LastEvaluatedKey")

    # Sort the results by created_at
    reverse_order = True if sort_order.upper() == "DESC" else False
    files.sort(key=lambda x: x.get("created_at", ""), reverse=reverse_order)

    # Encode last_evaluated_key to base64 if it's not null
    if last_evaluated_key:
        last_evaluated_key = base64.b64encode(
            json.dumps(last_evaluated_key).encode("utf-8")
        ).decode("utf-8")
        logger.info("Encoded last_evaluated_key: %s", last_evaluated_key)

    result = {
        "data": files,
        "last_evaluated_key": last_evaluated_key if last_evaluated_key else None,
    }

    logger.info("Returning response with %d files", len(files))
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(result, cls=DecimalEncoder),
    }
