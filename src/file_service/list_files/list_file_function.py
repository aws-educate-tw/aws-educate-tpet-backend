import json
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Or


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event, context):
    # Initialize query parameters with default values
    limit = 10
    last_evaluated_key = None
    order = "ASC"
    file_extensions = None

    # Extract query parameters if they exist
    if event.get("queryStringParameters"):
        limit = int(event["queryStringParameters"].get("limit", 10))
        last_evaluated_key = event["queryStringParameters"].get(
            "last_evaluated_key", None
        )
        order = event["queryStringParameters"].get("order", "ASC")
        file_extensions = event["queryStringParameters"].get("file_extensions", None)

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("file")

    scan_kwargs = {
        "Limit": limit,
    }

    filter_expression = None
    if file_extensions:
        extensions = file_extensions.split(",")
        filter_expression = Or(*(Attr("file_extension").eq(ext) for ext in extensions))

    if last_evaluated_key:
        scan_kwargs["ExclusiveStartKey"] = {"file_id": last_evaluated_key}

    if filter_expression:
        scan_kwargs["FilterExpression"] = filter_expression

    response = table.scan(**scan_kwargs)

    files = response.get("Items", [])
    last_evaluated_key = response.get("LastEvaluatedKey")

    result = {
        "data": files,
        "last_evaluated_key": last_evaluated_key if last_evaluated_key else None,
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result, cls=DecimalEncoder),
    }
