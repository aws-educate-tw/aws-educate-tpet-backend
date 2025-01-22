"""
This lambda function retrieves the details of a webhook from the DynamoDB table based on the
webhook ID provided in the path parameters. The function first extracts the webhook ID from the
event object and then fetches the webhook details using the WebhookRepository class. If the
webhook is found, the function constructs a response with the webhook details and returns it.
If the webhook is not found, the function returns a 404 response. If any unexpected errors occur
during the execution, the function logs the error and returns a 500 response.
"""

import json
import logging
from decimal import Decimal

from webhook_repository import WebhookRepository
from webhook_total_count_repository import WebhookTotalCountRepository
from webhook_type_enum import WebhookType

webhook_repository = WebhookRepository()
webhook_total_count_repository = WebhookTotalCountRepository()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON Encoder to handle Decimal types."""

    def default(self, o):
        if isinstance(o, Decimal):
            # Convert Decimal to float or int, depending on your needs
            return float(o)
        return super().default(o)


def lambda_handler(event: dict, context) -> dict:  # pylint: disable=unused-argument
    """
    Lambda function to fetch data from DynamoDB with optional limit, sort order, and pagination using sequence numbers.
    """
    query_params = event.get("queryStringParameters", {})
    limit = int(query_params.get("limit", 10))  # Default limit to 10
    sort_order = query_params.get("sort_order", "DESC").upper()  # Default to DESC
    page = int(query_params.get("page", 1))  # Default page number is 1
    webhook_type = query_params.get("webhook_type")  # Required parameter

    if not webhook_type or webhook_type.strip() == "":
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"error": "'webhook_type' parameter is required and cannot be empty."}
            ),
        }
    try:
        # Convert string webhook_type to Enum
        webhook_type_enum = WebhookType(webhook_type.lower())

    except ValueError:
        # Handle invalid webhook_type values
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "error": f"Invalid webhook_type value: {webhook_type}. Must be one of {[e.value for e in WebhookType]}."
                }
            ),
        }
    try:
        # Get total count from the total_count table
        total_count = webhook_total_count_repository.get_total_count(
            webhook_type_enum.value
        )
        if total_count == 0:
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {
                        "data": [],
                        "page": page,
                        "limit": limit,
                        "total_count": total_count,
                        "sort_order": sort_order,
                    }
                ),
            }

        # Validate page number
        if page < 1:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Invalid page number."}),
            }
        elif limit < 1:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Invalid limit value."}),
            }
        elif (page - 1) * limit >= total_count:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Page number out of range."}),
            }
        # Calculate start and end range for the page
        if sort_order == "ASC":
            start_key = (page - 1) * limit + 1
            end_key = min(page * limit, total_count)
        else:  # DESC
            start_key = max(total_count - (page * limit) + 1, 1)
            end_key = total_count - (page - 1) * limit

        data = webhook_repository.get_data(webhook_type, sort_order, start_key, end_key)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "data": data,
                    "page": page,
                    "limit": limit,
                    "total_count": total_count,
                    "sort_order": sort_order,
                },
                cls=DecimalEncoder,
            ),  # Use the custom encoder here
        }
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error occurred: %s", str(e))
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "error": "Internal server error.",
                    "message": str(e),
                }
            ),
        }
