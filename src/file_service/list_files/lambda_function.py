import base64
import json
import logging
from decimal import Decimal

import boto3
import botocore.exceptions
from boto3.dynamodb.conditions import Key

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("file")

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

# encode and decode functions for the key
def decode_key(encoded_key):
    try:
        decoded_key = json.loads(base64.b64decode(encoded_key).decode("utf-8"))
        return decoded_key
    except (json.JSONDecodeError, base64.binascii.Error) as e:
        logger.error("Invalid key format: %s", str(e))
        raise ValueError("Invalid key format. It must be a valid base64 encoded JSON string.")

def encode_key(decoded_key):
    encoded_key = base64.b64encode(json.dumps(decoded_key).encode("utf-8")).decode("utf-8")
    return encoded_key

def extract_query_params(event):
    limit = 10
    last_evaluated_key = None
    first_evaluated_key = None
    file_extension = None
    sort_order = "DESC"

    # Extract query parameters if they exist
    if event.get("queryStringParameters"):
        try:
            limit = int(event["queryStringParameters"].get("limit", 10))
            last_evaluated_key = event["queryStringParameters"].get("last_evaluated_key", None)
            first_evaluated_key = event["queryStringParameters"].get("first_evaluated_key", None)
            sort_order = event["queryStringParameters"].get("sort_order", "DESC")
            file_extension = event["queryStringParameters"].get("file_extension", None)
        except ValueError as e:
            logger.error("Invalid query parameter: %s", str(e))
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid query parameter: " + str(e)}),
            }
            
    # Log the extracted parameters
    logger.info(
        "Extracted parameters - limit: %d, last_evaluated_key: %s, first_evaluated_key: %s, sort_order: %s, file_extension: %s",
        limit,
        last_evaluated_key,
        first_evaluated_key,
        sort_order,
        file_extension,
    )
    
    return limit, last_evaluated_key, first_evaluated_key, file_extension, sort_order

def lambda_handler(event, context):
    """Lambda function handler for listing files."""
    limit, last_evaluated_key, first_evaluated_key, file_extension, sort_order = extract_query_params(event)

    query_kwargs = {
        "Limit": limit,
        "ScanIndexForward": False if sort_order.upper() == "DESC" else True,
    }

    if file_extension:
        query_kwargs.update({
            "IndexName": "file_extension-created_at-gsi",
            "KeyConditionExpression": Key("file_extension").eq(file_extension),
        })

    if last_evaluated_key:
        try:
            # Decode the base64 last_evaluated_key
            last_evaluated_key = decode_key(last_evaluated_key)
            query_kwargs["ExclusiveStartKey"] = last_evaluated_key
            logger.info("Decoded last_evaluated_key: %s", last_evaluated_key)
        except ValueError as e:
            logger.error("Invalid last_evaluated_key format: %s", str(e))
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"error": "Invalid last_evaluated_key format. It must be a valid base64 encoded JSON string."}
                ),
            }
            
    # Query the table using the provided parameters
    try:
        if file_extension:
            response = table.query(**query_kwargs)
            logger.info("Query successful")
        else:
            response = table.scan(**query_kwargs)
            logger.info("Scan successful")
    except botocore.exceptions.ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ValidationException":
            logger.error("Query/Scan failed: %s", str(e))
            return {"statusCode": 400, "body": json.dumps({"error": str(e)})}
        else:
            raise e

    files = response.get("Items", [])
    last_evaluated_key = response.get("LastEvaluatedKey")
    first_evaluated_key = files[0] if files else None

    # Sort the results by created_at
    reverse_order = True if sort_order.upper() == "DESC" else False
    files.sort(key=lambda x: x.get("created_at", ""), reverse=reverse_order)

    # Encode last_evaluated_key to base64 if it's not null
    for file in files:
        for key, value in file.items():
            if isinstance(value, Decimal):
                file[key] = float(value)
                
    # Encode last_evaluated_key and first_evaluated_key to base64 if they're not null
    if last_evaluated_key:
        last_evaluated_key = encode_key(last_evaluated_key)
        logger.info("Encoded last_evaluated_key: %s", last_evaluated_key)

    if first_evaluated_key:
        first_evaluated_key = encode_key(first_evaluated_key)
        logger.info("Encoded first_evaluated_key: %s", first_evaluated_key)

    result = {
        "data": files,
        "last_evaluated_key": last_evaluated_key if last_evaluated_key else None,
        "first_evaluated_key": first_evaluated_key if first_evaluated_key else None,
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
