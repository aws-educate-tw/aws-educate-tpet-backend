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
    AWS Lambda handler function to handle both forced password change for first login and password reset for forgot password.

    Args:
        event (dict): Event data containing the request body with account, new password, session, verification_code, and any required attributes.
        context (dict): Context data (unused).

    Returns:
        dict: Response object with status code, headers, and body.
    """
    try:
        # Parse the request body
        body = json.loads(event["body"])
        account = body.get("account")
        new_password = body.get("new_password")

        # Handle first login forced password change (NEW_PASSWORD_REQUIRED) scenario
        if "session" in body:
            session = body["session"]
            response = client.respond_to_auth_challenge(
                ClientId=COGNITO_CLIENT_ID,
                ChallengeName="NEW_PASSWORD_REQUIRED",
                Session=session,
                ChallengeResponses={
                    "USERNAME": account,
                    "NEW_PASSWORD": new_password,
                    # Add any required attributes if necessary
                },
            )
            logger.info("Password changed successfully for first login.")
            access_token = response["AuthenticationResult"]["AccessToken"]

            return {
                "statusCode": 200,
                "headers": {
                    "Set-Cookie": f"accessToken={access_token}; Path=/; Secure; HttpOnly; SameSite=None; Domain=.yourdomain.com"
                },
                "body": json.dumps(
                    {"message": "Password changed successfully (First Login)"}
                ),
            }

        # Handle forgot password reset scenario (using verification code)
        elif "verification_code" in body:
            verification_code = body["verification_code"]
            response = client.confirm_forgot_password(
                ClientId=COGNITO_CLIENT_ID,
                Username=account,
                ConfirmationCode=verification_code,
                Password=new_password,
            )
            logger.info("Password reset successfully using verification code.")
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"message": "Password reset successfully (Forgot Password)"}
                ),
            }

        else:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"message": "Missing required parameters for password change."}
                ),
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
