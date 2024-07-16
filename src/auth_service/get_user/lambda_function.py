import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE")

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)


def lambda_handler(event, context):

    user_id = event["pathParameters"]["user_id"]

    try:
        response = table.get_item(Key={"user_id": user_id})

        if "Item" not in response:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "User not found"}),
                "headers": {"Content-Type": "application/json"},
            }

        user_data = response["Item"]

        return {
            "statusCode": 200,
            "body": json.dumps(user_data),
            "headers": {"Content-Type": "application/json"},
        }

    except ClientError as e:
        logger.error("Error fetching user data: %s", e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
            "headers": {"Content-Type": "application/json"},
        }
