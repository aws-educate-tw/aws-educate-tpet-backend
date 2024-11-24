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
        dict: Result of the refresh operation containing:
            - service_account: Name of the service account
            - status: 'success' or 'failed'
            - message: Success message or error details

    Raises:
        ClientError: If AWS service interaction fails
        ValueError: If the login response is invalid
    """
    try:
        logger.info("Starting token refresh for service account: %s", service_account)

        # Retrieve service account password from Secrets Manager
        password_response = secrets_client.get_secret_value(
            SecretId=get_secret_path(service_account, "password")
        )
        password = json.loads(password_response["SecretString"])["password"]

        # Prepare login payload with complete API Gateway format
        login_payload = {
            "headers": {"Content-Type": "application/json"},
            "httpMethod": "POST",
            "body": json.dumps({"account": service_account, "password": password}),
            "requestContext": {"http": {"method": "POST"}},
        }

        login_response = lambda_client.invoke(
            FunctionName=LOGIN_FUNCTION_ARN,
            InvocationType="RequestResponse",
            Payload=json.dumps(login_payload),
        )

        # Check for Lambda execution errors
        if "FunctionError" in login_response:
            error_detail = login_response.get("Payload").read().decode()
            raise ValueError(f"Lambda execution failed: {error_detail}")

        login_result = json.loads(login_response["Payload"].read().decode())

        # Parse login Lambda response
        try:
            if isinstance(login_result, dict):
                # Handle API Gateway response format
                if "statusCode" in login_result:
                    if login_result["statusCode"] != 200:
                        raise ValueError(
                            f"Login failed with status {login_result['statusCode']}: {login_result.get('body')}"
                        )
                    response_body = json.loads(login_result["body"])
                    access_token = response_body["access_token"]
                # Handle direct Lambda response format
                elif "access_token" in login_result:
                    access_token = login_result["access_token"]
                else:
                    raise ValueError(f"Invalid response format: {login_result}")
            else:
                raise ValueError(f"Unexpected response type: {type(login_result)}")

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse login response: {str(e)}")

        # Store the new access token in Secrets Manager
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
    This function iterates through all configured service accounts and refreshes their access tokens.

    Args:
        event (dict): Event data passed to the Lambda function (unused)
        context (dict): Runtime information provided by AWS Lambda (unused)

    Returns:
        dict: Response object containing:
            - statusCode: 200 for success, 500 if any refresh operation failed
            - body: JSON string containing detailed results and summary
    """
    results = []
    has_failures = False

    # Process each service account
    for service_account in SERVICE_ACCOUNTS:
        result = refresh_service_account_access_token(service_account)
        results.append(result)
        if result["status"] == "failed":
            has_failures = True

    # Prepare response with summary
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
