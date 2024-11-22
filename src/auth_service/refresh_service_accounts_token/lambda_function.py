import json
import logging
import os
from typing import Dict

import boto3
from botocore.exceptions import ClientError

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secrets_client = boto3.client("secretsmanager")
lambda_client = boto3.client("lambda")

# Environment variables
LOGIN_FUNCTION_ARN = os.getenv("LOGIN_FUNCTION_ARN")
ENVIRONMENT = os.getenv("ENVIRONMENT")

# List of service accounts that need token refresh
SERVICE_ACCOUNTS = [
    "surveycake",
]


def get_secret_path(service_account: str, secret_type: str) -> str:
    """
    Generate secret path based on environment and service account.

    Args:
        service_account (str): Name of the service account (e.g., 'surveycake', 'slack')
        secret_type (str): Type of secret ("password" or "access-token")

    Returns:
        str: Full secret path in Secrets Manager
    """
    return f"aws-educate-tpet/{ENVIRONMENT}/service-accounts/{service_account}/{secret_type}"


def refresh_service_account_access_token(service_account: str) -> Dict:
    """
    Refresh access token for a specific service account.

    Args:
        service_account (str): Name of the service account to refresh token for

    Returns:
        dict: Result of the refresh operation

    Raises:
        ClientError: If AWS service interaction fails
        ValueError: If the refresh operation fails
    """
    try:
        logger.info("Starting token refresh for service account: %s", service_account)

        # Get password
        password_response = secrets_client.get_secret_value(
            SecretId=get_secret_path(service_account, "password")
        )
        password = json.loads(password_response["SecretString"])["password"]

        # Get new token
        login_payload = {
            "body": json.dumps({"account": service_account, "password": password})
        }

        login_response = lambda_client.invoke(
            FunctionName=LOGIN_FUNCTION_ARN,
            InvocationType="RequestResponse",
            Payload=json.dumps(login_payload),
        )

        login_result = json.loads(login_response["Payload"].read().decode())

        if login_result["statusCode"] != 200:
            raise ValueError(f"Login failed: {login_result['body']}")

        access_token = json.loads(login_result["body"])["access_token"]

        # Update access token
        secret_data = {"account": service_account, "access_token": access_token}

        secrets_client.update_secret(
            SecretId=get_secret_path(service_account, "access-token"),
            SecretString=json.dumps(secret_data),
        )

        logger.info("Token refresh successful for service account: %s", service_account)
        return {
            "service_account": service_account,
            "status": "success",
            "message": "Token refresh successful",
        }

    except (ClientError, ValueError) as e:
        logger.error(
            "Token refresh failed for service account %s: %s", service_account, str(e)
        )
        return {"service_account": service_account, "status": "failed", "error": str(e)}


def lambda_handler(event, context):
    """
    AWS Lambda handler function to refresh access tokens for all service accounts.

    Args:
        event (dict): Event data (unused)
        context (dict): Context data (unused)

    Returns:
        dict: Response object with status code and body containing results for all service accounts
    """
    results = []
    has_failures = False

    for service_account in SERVICE_ACCOUNTS:
        result = refresh_service_account_access_token(service_account)
        results.append(result)
        if result["status"] == "failed":
            has_failures = True

    response_body = {
        "results": results,
        "summary": {
            "total": len(results),
            "successful": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "failed"]),
        },
    }

    return {
        "statusCode": 500 if has_failures else 200,
        "body": json.dumps(response_body),
    }
