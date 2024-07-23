import json
import logging
import os

import boto3
import jwt
from botocore.exceptions import ClientError

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE")
table = dynamodb.Table(DYNAMODB_TABLE)


def lambda_handler(event, context):
    """
    Lambda function to handle GET /users/me API request.

    This function reads the accessToken from cookies, decodes the JWT to get the user_id (sub),
    and retrieves the user data from DynamoDB using the user_id.

    Parameters:
    event (dict): API Gateway Lambda Proxy Input Format
    context (LambdaContext): Lambda Context runtime methods and attributes

    Returns:
    dict: API Gateway Lambda Proxy Output Format
    """

    # Get accessToken from cookies
    cookies = event.get("headers", {}).get("Cookie", "")
    access_token = None
    for cookie in cookies.split(";"):
        if "accessToken=" in cookie:
            access_token = cookie.split("=")[1]
            break

    if not access_token:
        return {
            "statusCode": 401,
            "body": json.dumps({"error": "Access token is missing"}),
            "headers": {"Content-Type": "application/json"},
        }

    try:
        # Decode JWT to get user_id (sub)
        decoded_token = jwt.decode(access_token, options={"verify_signature": False})
        user_id = decoded_token.get("sub")

        if not user_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid access token"}),
                "headers": {"Content-Type": "application/json"},
            }

        # Fetch user data from DynamoDB using user_id
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

    except jwt.ExpiredSignatureError:
        return {
            "statusCode": 401,
            "body": json.dumps({"error": "Access token has expired"}),
            "headers": {"Content-Type": "application/json"},
        }

    except jwt.InvalidTokenError:
        return {
            "statusCode": 401,
            "body": json.dumps({"error": "Invalid access token"}),
            "headers": {"Content-Type": "application/json"},
        }
