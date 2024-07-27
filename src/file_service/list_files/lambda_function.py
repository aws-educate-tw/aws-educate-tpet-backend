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
pagination_state_table = dynamodb.Table("file_service_pagination_state")


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
        raise ValueError(
            "Invalid key format. It must be a valid base64 encoded JSON string."
        )


def encode_key(decoded_key):
    encoded_key = base64.b64encode(json.dumps(decoded_key).encode("utf-8")).decode(
        "utf-8"
    )
    return encoded_key


def extract_query_params(event):
    limit = 10
    last_evaluated_key = None
    file_extension = None
    sort_order = "DESC"

    # Extract query parameters if they exist
    if event.get("queryStringParameters"):
        try:
            limit = int(event["queryStringParameters"].get("limit", 10))
            last_evaluated_key = event["queryStringParameters"].get(
                "last_evaluated_key", None
            )
            sort_order = event["queryStringParameters"].get("sort_order", "DESC")
            file_extension = event["queryStringParameters"].get("file_extension", None)
        except ValueError as e:
            logger.error("Invalid query parameter: %s", str(e))
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Invalid query parameter: " + str(e)}),
            }

    if not file_extension:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {"message": "file_extension is a required query parameter"}
            ),
        }

    # Log the extracted parameters
    logger.info(
        "Extracted parameters - limit: %d, last_evaluated_key: %s, sort_order: %s, file_extension: %s",
        limit,
        last_evaluated_key,
        sort_order,
        file_extension,
    )

    return limit, last_evaluated_key, file_extension, sort_order


def store_pagination_state(
    user_id,
    previous_last_evaluated_key,
    current_last_evaluated_key,
    next_last_evaluated_key,
):
    pagination_state_table.put_item(
        Item={
            "user_id": user_id,
            "previous_last_evaluated_key": previous_last_evaluated_key,
            "current_last_evaluated_key": current_last_evaluated_key,
            "next_last_evaluated_key": next_last_evaluated_key,
        }
    )


def get_pagination_state(user_id):
    response = pagination_state_table.get_item(
        Key={
            "user_id": user_id,
        }
    )
    return response.get("Item", {})


def lambda_handler(event, context):
    """Lambda function handler for listing files."""
    extracted_params = extract_query_params(event)
    if isinstance(extracted_params, dict) and extracted_params.get("statusCode"):
        return extracted_params

    limit, last_evaluated_key, file_extension, sort_order = extracted_params
    user_id = "dummy_uploader_id"

    query_kwargs = {
        "Limit": limit,
        "ScanIndexForward": False if sort_order.upper() == "DESC" else True,
        "IndexName": "file_extension-created_at-gsi",
    }

    query_kwargs["KeyConditionExpression"] = Key("file_extension").eq(file_extension)

    if last_evaluated_key:
        try:
            # Decode the base64 last_evaluated_key
            current_last_evaluated_key = last_evaluated_key
            last_evaluated_key = decode_key(last_evaluated_key)
            query_kwargs["ExclusiveStartKey"] = last_evaluated_key
            logger.info("Decoded last_evaluated_key: %s", last_evaluated_key)

            # Get the previous last evaluated key from the state
            state = get_pagination_state(user_id)
            previous_last_evaluated_key = state.get("previous_last_evaluated_key")
        except ValueError as e:
            logger.error("Invalid last_evaluated_key format: %s", str(e))
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "message": "Invalid last_evaluated_key format. It must be a valid base64 encoded JSON string."
                    }
                ),
            }
    else:
        current_last_evaluated_key = None
        previous_last_evaluated_key = None

    # Query the table using the provided parameters
    try:
        response = table.query(**query_kwargs)
        logger.info("Query successful")
    except botocore.exceptions.ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ValidationException":
            logger.error("Query failed: %s", str(e))
            return {"statusCode": 400, "body": json.dumps({"message": str(e)})}
        else:
            raise e

    files = response.get("Items", [])
    next_last_evaluated_key = response.get("LastEvaluatedKey")

    # Encode last_evaluated_key to base64 if it's not null
    if next_last_evaluated_key:
        next_last_evaluated_key = encode_key(next_last_evaluated_key)

    # Store the pagination state for the next request
    store_pagination_state(
        user_id,
        current_last_evaluated_key,
        next_last_evaluated_key,
        next_last_evaluated_key,
    )

    # Sort the results by created_at
    reverse_order = True if sort_order.upper() == "DESC" else False
    files.sort(key=lambda x: x.get("created_at", ""), reverse=reverse_order)

    # Encode last_evaluated_key to base64 if it's not null
    for file in files:
        for key, value in file.items():
            if isinstance(value, Decimal):
                file[key] = float(value)

    result = {
        "data": files,
        "previous_last_evaluated_key": (
            previous_last_evaluated_key if previous_last_evaluated_key else None
        ),
        "current_last_evaluated_key": (
            current_last_evaluated_key if current_last_evaluated_key else None
        ),
        "next_last_evaluated_key": (
            next_last_evaluated_key if next_last_evaluated_key else None
        ),
    }

    logger.info("Returning response with %d files", len(files))
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(result, cls=DecimalEncoder),
    }
