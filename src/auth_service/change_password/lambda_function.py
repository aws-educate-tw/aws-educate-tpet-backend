import json
import logging

import boto3
from botocore.exceptions import ClientError

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    AWS Lambda handler function to change the password for a user with Cognito.

    Args:
        event (dict): Event data containing the request body with username, new password, session, and any required attributes.
        context (dict): Context data (unused).

    Returns:
        dict: Response object with status code, headers, and body.
    """
    client = boto3.client("cognito-idp")
    try:
        # Parse the request body
        body = json.loads(event["body"])

        # Respond to the new password required challenge
        response = client.respond_to_auth_challenge(
            ClientId="2hd882ob3m7kjb5bjrklejjiu4",
            ChallengeName="NEW_PASSWORD_REQUIRED",
            Session=body["session"],
            ChallengeResponses={
                "USERNAME": body["username"],
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
