import base64
import json
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("TABLE_NAME"))


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event, context):
    # Initialize query parameters with default values
    limit = 10
    last_evaluated_key = None
    file_extension = None
    sort_by = "created_at"
    sort_order = "DESC"

    # Extract query parameters if they exist
    if event.get("queryStringParameters"):
        limit = int(event["queryStringParameters"].get("limit", 10))
        last_evaluated_key = event["queryStringParameters"].get(
            "last_evaluated_key", None
        )
        sort_by = event["queryStringParameters"].get("sort_by", "created_at")
        sort_order = event["queryStringParameters"].get("sort_order", "DESC")
        file_extension = event["queryStringParameters"].get("file_extension", None)

    scan_kwargs = {
        "Limit": limit,
    }

    filter_expression = None
    if file_extension:
        extensions = file_extension.split(",")
        filter_expressions = [Attr("file_extension").eq(ext) for ext in extensions]
        filter_expression = filter_expressions[0]
        for expr in filter_expressions[1:]:
            filter_expression = filter_expression | expr
        scan_kwargs["FilterExpression"] = filter_expression

    if last_evaluated_key:
        try:
            # Decode the base64 last_evaluated_key
            last_evaluated_key = json.loads(
                base64.b64decode(last_evaluated_key).decode("utf-8")
            )
            scan_kwargs["ExclusiveStartKey"] = last_evaluated_key
        except (json.JSONDecodeError, base64.binascii.Error):
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": "Invalid last_evaluated_key format. It must be a valid base64 encoded JSON string."
                    }
                ),
            }

    response = table.scan(**scan_kwargs)

    files = response.get("Items", [])
    last_evaluated_key = response.get("LastEvaluatedKey")

    # Sort the results
    reverse_order = True if sort_order.upper() == "DESC" else False
    files.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse_order)

    # Encode last_evaluated_key to base64 if it's not null
    if last_evaluated_key:
        last_evaluated_key = base64.b64encode(
            json.dumps(last_evaluated_key).encode("utf-8")
        ).decode("utf-8")

    result = {
        "data": files,
        "last_evaluated_key": last_evaluated_key if last_evaluated_key else None,
    }

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(result, cls=DecimalEncoder),
    }
