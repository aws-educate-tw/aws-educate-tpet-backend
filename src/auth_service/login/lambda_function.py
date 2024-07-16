import json
import logging

import boto3
from botocore.exceptions import ClientError

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    AWS Lambda handler function to authenticate a user with Cognito.

    Args:
        event (dict): Event data containing the request body with username and password.
        context (dict): Context data (unused).

    Returns:
        dict: Response object with status code, headers, and body.
    """
    client = boto3.client("cognito-idp")
    try:
        # Parse the request body
        body = json.loads(event["body"])

        # Initiate authentication with Cognito
        response = client.initiate_auth(
            ClientId="2hd882ob3m7kjb5bjrklejjiu4",
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": body["username"], "PASSWORD": body["password"]},
        )

        logger.info("Cognito auth response: %s", response)

        # Check if a new password is required
        if response.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
            return {
                "statusCode": 200,
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

        # Return successful response with the access token set in cookies
        return {
            "statusCode": 200,
            "headers": {
                "Set-Cookie": f"accessToken={access_token}; Path=/; Secure; HttpOnly; SameSite=None; Domain=.aws-educate.tw"
            },
            "body": json.dumps({"message": "Login successful"}),
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
