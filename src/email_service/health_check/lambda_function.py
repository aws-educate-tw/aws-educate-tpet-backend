import datetime
import json
import logging
import os

from run_repository import RunRepository

# Initialize Logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Time format for ISO 8601
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Environment variables
SERVICE = os.getenv("SERVICE", "unknown_service")  # Underscore format
ENVIRONMENT = os.getenv("ENVIRONMENT", "unknown_environment")


def format_service_name(service_name: str) -> str:
    """
    Convert service name from underscore format to hyphen format for external output.

    Args:
        service_name (str): Original service name (e.g., "auth_service")

    Returns:
        str: Formatted service name (e.g., "auth-service")
    """
    return service_name.replace("_", "-")


def lambda_handler(event: dict, context) -> dict:
    """
    Main Lambda handler for health check endpoint.
    Returns the health status of the service.

    Args:
        event (dict): AWS Lambda event object
        context: AWS Lambda context object

    Returns:
        dict: Lambda response containing health check status
    """
    try:
        formatted_service_name = format_service_name(SERVICE)
        logger.info("Health check started for service: %s", formatted_service_name)

        repo = RunRepository()
        if repo.check_connection():
            status = "HEALTHY"
            message = "Aurora database connection successful"
        else:
            status = "UNHEALTHY"
            message = "Aurora database connection failed"

        # Build health check response
        health_status = {
            "status": status,
            "message": message,
            "service": formatted_service_name,
            "environment": ENVIRONMENT,
            "checked_at": datetime.datetime.now(datetime.UTC).strftime(TIME_FORMAT),
        }

        logger.info("Health check result: %s", json.dumps(health_status))

        # Return health check response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps(health_status),
        }
    except Exception as e:
        logger.error("Error occurred during health check: %s", e)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps({"error": str(e)}),
        }
