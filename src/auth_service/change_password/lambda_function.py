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


def lambda_handler(event, context):
    """
    AWS Lambda handler function to change the password for a user with Cognito.

    Args:
        event (dict): Event data containing the request body with account, new password, session, and any required attributes.
        context (dict): Context data (unused).

    Returns:
        dict: Response object with status code, headers, and body.
    """
    try:
        # Parse the request body
        body = json.loads(event["body"])

        # Respond to the new password required challenge
        response = client.respond_to_auth_challenge(
            ClientId=COGNITO_CLIENT_ID,
            ChallengeName="NEW_PASSWORD_REQUIRED",
            Session=body["session"],
            ChallengeResponses={
                "USERNAME": body["account"],
                "NEW_PASSWORD": body["new_password"],
                # Add any required attributes here if necessary
            },
        )

        logger.info("Cognito respond to challenge response: %s", response)

        # Extract access token from the response
        access_token = response["AuthenticationResult"]["AccessToken"]

        # Return successful response with the access token set in cookies
        return {
            "statusCode": 200,
            "headers": {
                "Set-Cookie": f"accessToken={access_token}; Path=/; Secure; HttpOnly; SameSite=None; Domain=.aws-educate.tw"
            },
            "body": json.dumps({"message": "Password changed successfully"}),
        }
    except ClientError as e:
        # Handle Cognito client errors
        logger.error("Cognito client error: %s", e)
        return {
            "statusCode": 400,
            "body": json.dumps({"message": e.response["Error"]["Message"]}),
        }
    except json.JSONDecodeError as e:
        # Handle JSON decoding errors
        logger.error("JSON decode error: %s", e)
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid JSON format in request body"}),
        }
