import base64
import json
import logging
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("email")


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def list_runs(start_date, end_date, uploader_id, sort_by, sort_order, limit, last_evaluated_key, first_evaluated_key):
    """
    List email records based on various parameters.

    :param start_date: The start date to filter records.
    :param end_date: The end date to filter records.
    :param uploader_id: The uploader ID to filter records.
    :param sort_by: The attribute to sort by.
    :param sort_order: The order of sorting (ASC or DESC).
    :param limit: The maximum number of records to return.
    :param last_evaluated_key: The last evaluated key for pagination.
    :param first_evaluated_key: The first evaluated key for pagination (not used in this function).
    :return: A list of email records and the last evaluated key.
    """
    query_kwargs = {
        "Limit": limit,
        "ScanIndexForward": False if sort_order.upper() == "DESC" else True,
    }

    key_conditions = Key("run_id").eq(uploader_id) & Key("created_at").between(start_date, end_date)

    query_kwargs["KeyConditionExpression"] = key_conditions

    if last_evaluated_key:
        try:
            # Decode the base64 last_evaluated_key
            last_evaluated_key = json.loads(base64.b64decode(last_evaluated_key).decode("utf-8"))
            query_kwargs["ExclusiveStartKey"] = last_evaluated_key
            logger.info("Decoded last_evaluated_key: %s", last_evaluated_key)
        except (json.JSONDecodeError, base64.binascii.Error) as e:
            logger.error("Invalid last_evaluated_key format: %s", str(e))
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Invalid last_evaluated_key format. It must be a valid base64 encoded JSON string."
                })
            }

    # Query the table using the provided parameters
    try:
        response = table.query(**query_kwargs)
        logger.info("Query successful")
    except boto3.exceptions.Boto3Error as e:
        logger.error("Query failed: %s", str(e))
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    records = response.get("Items", [])
    last_evaluated_key = response.get("LastEvaluatedKey")

    # Sort the results if sort_by is specified
    if sort_by:
        reverse_order = True if sort_order.upper() == "DESC" else False
        records.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse_order)

    # Encode last_evaluated_key to base64 if it's not null
    if last_evaluated_key:
        last_evaluated_key = base64.b64encode(json.dumps(last_evaluated_key).encode("utf-8")).decode("utf-8")
        logger.info("Encoded last_evaluated_key: %s", last_evaluated_key)

    result = {
        "data": records,
        "last_evaluated_key": last_evaluated_key if last_evaluated_key else None,
    }

    return result



def lambda_handler(event, context):
    """Lambda function handler for listing runs."""
    try:
        query_params = event.get("queryStringParameters", {})

        start_date = query_params.get("start_date")
        end_date = query_params.get("end_date")
        uploader_id = query_params.get("uploader_id")
        sort_by = query_params.get("sort_by", "created_at")
        sort_order = query_params.get("sort_order", "DESC")
        limit = int(query_params.get("limit", 10))
        last_evaluated_key = query_params.get("last_evaluated_key", None)
        first_evaluated_key = query_params.get("first_evaluated_key", None)

        if not start_date or not end_date:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "start_date and end_date are required parameters."})
            }

        result = list_runs(start_date, end_date, uploader_id, sort_by, sort_order, limit, last_evaluated_key, first_evaluated_key)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(result, cls=DecimalEncoder),
        }
    except Exception as e:
        error_message = str(e)
        logger.error("Exception: %s", error_message, exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": error_message})}
