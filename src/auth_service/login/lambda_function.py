import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client("cognito-idp")

COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
ENVIRONMENT = os.getenv("ENVIRONMENT")

# Define allowed origins
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5500",
    "https://aws-educate.tw",
    "https://vercel.app",
]


def lambda_handler(event, context):
    """
    AWS Lambda handler function to authenticate a user with Cognito.

    Args:
      event (dict): Event data containing the request body with account and password.
      context (dict): Context data (unused).

    Returns:
      dict: Response object with status code, headers, and body.
    """
    # Identify if the incoming event is a prewarm request
    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}
    try:
        logger.info("Event: %s", event)

        # Get the origin of the request
        origin = event["headers"].get("origin")

        # Handle OPTIONS preflight request
        if event["httpMethod"] == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                    "Access-Control-Allow-Credentials": "true",
                },
                "body": "",
            }

        # Check if the body exists
        if event.get("body") is None:
            raise ValueError("Request body is missing")

        # Parse the request body
        body = json.loads(event["body"])

        # Initiate authentication with Cognito
        response = client.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": body["account"], "PASSWORD": body["password"]},
        )

        logger.info("Cognito auth response: %s", response)

        # Check if a new password is required
        if response.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Credentials": "true",
                },
                "body": json.dumps(
                    {
                        "message": "New password required",
                        "challengeName": response["ChallengeName"],
                        "session": response["Session"],
                        "challengeParameters": response["ChallengeParameters"],
                    }
                ),
            }

        # Extract access token from the response
        access_token = response["AuthenticationResult"]["AccessToken"]

        # Define the domains and secure attribute based on environment
        if ENVIRONMENT in ["dev", "local-dev", "preview"]:
            domains = ["localhost", ".aws-educate.tw", ".vercel.app"]
            secure_attribute = ""
        else:
            domains = [".aws-educate.tw"]
            secure_attribute = "Secure; "

        # Calculate the expiry time (7 days in seconds)
        max_age = 7 * 24 * 60 * 60  # 7 days in seconds

        # Create the Set-Cookie headers for each domain
        set_cookie_headers = [
            f"accessToken={access_token}; Path=/; {secure_attribute}HttpOnly; SameSite=None; Domain={domain}; Max-Age={max_age}"
            for domain in domains
        ]

        # Return successful response with the access token set in cookies
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
            },
            "multiValueHeaders": {"Set-Cookie": set_cookie_headers},
            "body": json.dumps(
                {"message": "Login successful", "access_token": access_token}
            ),
        }
    except ClientError as e:
        # Handle Cognito client errors
        logger.error("Cognito client error: %s", e)
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
            },
            "body": json.dumps({"message": e.response["Error"]["Message"]}),
        }
    except json.JSONDecodeError as e:
        # Handle JSON decoding errors
        logger.error("JSON decode error: %s", e)
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
            },
            "body": json.dumps({"message": "Invalid JSON format in request body"}),
        }
    except ValueError as e:
        # Handle missing body error
        logger.error("ValueError: %s", e)
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
            },
            "body": json.dumps({"message": str(e)}),
        }
