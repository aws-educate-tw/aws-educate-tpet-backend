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

    This function reads the JWT from the Authorization header, decodes it to get the user_id (sub),
    and retrieves the user data from DynamoDB using the user_id.

    Parameters:
    event (dict): API Gateway Lambda Proxy Input Format
    context (LambdaContext): Lambda Context runtime methods and attributes

    Returns:
    dict: API Gateway Lambda Proxy Output Format
    """
    # Identify if the incoming event is a prewarm request
    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    # Get JWT token from Authorization header
    authorization_header = event.get("headers", {}).get("authorization", "")
    if not authorization_header.startswith("Bearer "):
        return {
            "statusCode": 401,
            "body": json.dumps(
                {"message": "Authorization header is missing or invalid"}
            ),
            "headers": {"Content-Type": "application/json"},
        }

    # Extract token from Authorization header
    jwt_token = authorization_header.split(" ")[1]

    try:
        # Decode JWT to get user_id (sub)
        decoded_token = jwt.decode(jwt_token, options={"verify_signature": False})
        user_id = decoded_token.get("sub")

        if not user_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Invalid JWT token"}),
                "headers": {"Content-Type": "application/json"},
            }

        # Fetch user data from DynamoDB using user_id
        response = table.get_item(Key={"user_id": user_id})

        if "Item" not in response:
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "User not found"}),
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
            "body": json.dumps({"message": "Internal server error"}),
            "headers": {"Content-Type": "application/json"},
        }

    except jwt.ExpiredSignatureError:
        return {
            "statusCode": 401,
            "body": json.dumps({"message": "JWT token has expired"}),
            "headers": {"Content-Type": "application/json"},
        }

    except jwt.InvalidTokenError:
        return {
            "statusCode": 401,
            "body": json.dumps({"message": "Invalid JWT token"}),
            "headers": {"Content-Type": "application/json"},
        }
