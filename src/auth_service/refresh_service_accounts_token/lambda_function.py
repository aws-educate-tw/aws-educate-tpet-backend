import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secrets_client = boto3.client("secretsmanager")
lambda_client = boto3.client("lambda")

# Environment variables
AUTH_LOGIN_FUNCTION = os.getenv("AUTH_LOGIN_FUNCTION")
SERVICE_ACCOUNT_SECRET_NAME = os.getenv("SERVICE_ACCOUNT_SECRET_NAME")


def get_service_account_password():
    """
    Get service account password from AWS Secrets Manager.

    Returns:
        str: The password stored in Secrets Manager.

    Raises:
        ClientError: If there's an error retrieving the secret.
    """
    try:
        response = secrets_client.get_secret_value(SecretId=SERVICE_ACCOUNT_SECRET_NAME)
        secret_data = json.loads(response["SecretString"])
        return secret_data["password"]
    except ClientError as e:
        logger.error("Failed to get password from Secrets Manager: %s", e)
        raise


def get_access_token(password):
    """
    Invoke auth login lambda to get access token.

    Args:
        password (str): Service account password.

    Returns:
        str: The access token from login response.

    Raises:
        ClientError: If Lambda invocation fails.
        ValueError: If the login response is invalid.
    """
    try:
        payload = {"body": json.dumps({"account": "surveycake", "password": password})}

        response = lambda_client.invoke(
            FunctionName=AUTH_LOGIN_FUNCTION,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        response_payload = json.loads(response["Payload"].read().decode())

        if response_payload["statusCode"] != 200:
            logger.error(
                "Login failed with status %d: %s",
                response_payload["statusCode"],
                response_payload["body"],
            )
            raise ValueError("Login request failed")

        body = json.loads(response_payload["body"])
        return body["access_token"]

    except ClientError as e:
        logger.error("Lambda invocation failed: %s", e)
        raise


def update_access_token(access_token):
    """
    Update access token in Secrets Manager.

    Args:
        access_token (str): New access token to store.

    Raises:
        ClientError: If there's an error updating the secret.
    """
    try:
        secret_data = {"access_token": access_token, "account": "surveycake"}

        secrets_client.update_secret(
            SecretId=SERVICE_ACCOUNT_SECRET_NAME, SecretString=json.dumps(secret_data)
        )

    except ClientError as e:
        logger.error("Failed to update token in Secrets Manager: %s", e)
        raise


def lambda_handler(event, context):
    """
    AWS Lambda handler function to refresh service account access token.

    Args:
        event (dict): Event data (unused).
        context (dict): Context data (unused).

    Returns:
        dict: Response object with status code and body.
    """
    try:
        # Get password from Secrets Manager
        password = get_service_account_password()

        # Get new access token via Lambda invocation
        access_token = get_access_token(password)

        # Update access token in Secrets Manager
        update_access_token(access_token)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Token refresh successful"}),
        }

    except ClientError as e:
        logger.error("AWS service error: %s", e)
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"message": "Failed to interact with AWS services", "error": str(e)}
            ),
        }
    except ValueError as e:
        logger.error("Value error: %s", e)
        return {"statusCode": 400, "body": json.dumps({"message": str(e)})}
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"message": "An unexpected error occurred", "error": str(e)}
            ),
        }
