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
    file_extension = None
    order = "DESC"

    # Extract query parameters if they exist
    if event.get("queryStringParameters"):
        limit = int(event["queryStringParameters"].get("limit", 10))
        last_evaluated_key = event["queryStringParameters"].get(
            "last_evaluated_key", None
        )
        order = event["queryStringParameters"].get("order", order)
        file_extension = event["queryStringParameters"].get("file_extension", None)

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("file")

    scan_kwargs = {
        "Limit": limit,
    }

    filter_expression = None
    expression_attribute_values = {}
    if file_extension:
        extensions = file_extension.split(",")
        filter_expressions = [Attr("file_extension").eq(ext) for ext in extensions]
        filter_expression = filter_expressions[0]
        for expr in filter_expressions[1:]:
            filter_expression = filter_expression | expr
        expression_attribute_values = {
            f":ext{i}": ext for i, ext in enumerate(extensions)
        }

        scan_kwargs["FilterExpression"] = filter_expression

    if last_evaluated_key:
        scan_kwargs["ExclusiveStartKey"] = {"file_id": last_evaluated_key}

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
