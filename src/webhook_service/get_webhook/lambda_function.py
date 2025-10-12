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

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize the repository
webhook_repository = WebhookRepository()


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON Encoder to handle Decimal types."""

    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def lambda_handler(event, context):  # pylint: disable=unused-argument
    """
    AWS Lambda function to retrieve webhook details.
    Args:
        event (dict): Lambda event object.
        context (object): Lambda context object (not used in this implementation).
    Returns:
        dict: Response with webhook details or an error message.
    """
    try:
        # Extract webhook ID from the path parameters
        webhook_id = event.get("pathParameters", {}).get("webhook_id")
        if not webhook_id:
            logger.error("Webhook ID not provided in path parameters.")
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Webhook ID is required."}),
            }

        # Fetch webhook details from the repository
        webhook_details = webhook_repository.get_item(webhook_id)
        if webhook_details is None:
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "Webhook not found"}),
            }

        # Retrieve the item details
        webhook_details_item = webhook_details.get("Item", {})
        logger.info("Webhook details: %s", webhook_details_item)

        # Prepare the response data
        data = {
            "webhook_id": webhook_details_item.get("webhook_id"),
            "webhook_url": webhook_details_item.get("webhook_url"),
            "subject": webhook_details_item.get("subject"),
            "display_name": webhook_details_item.get("display_name"),
            "template_file_id": webhook_details_item.get("template_file_id"),
            "is_generate_certificate": webhook_details_item.get(
                "is_generate_certificate"
            ),
            "reply_to": webhook_details_item.get("reply_to"),
            "sender_local_part": webhook_details_item.get("sender_local_part"),
            "attachment_file_ids": webhook_details_item.get("attachment_file_ids"),
            "bcc": webhook_details_item.get("bcc"),
            "cc": webhook_details_item.get("cc"),
            "surveycake_link": webhook_details_item.get("surveycake_link"),
            "hash_key": webhook_details_item.get("hash_key"),
            "iv_key": webhook_details_item.get("iv_key"),
            "webhook_name": webhook_details_item.get("webhook_name"),
            "webhook_type": webhook_details_item.get("webhook_type"),
            "run_id": webhook_details_item.get("run_id"),
        }

        # Return the successful response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "status": "SUCCESS",
                    "message": "The details of the webhook are successfully retrieved.",
                    **data,
                },
                cls=DecimalEncoder,
            ),
        }

    except Exception as e:  # pylint: disable=broad-except
        # Log unexpected errors
        logger.error("An unexpected error occurred: %s", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Internal server error"}),
        }
