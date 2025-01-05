"""
This lamda function creates a new webhook in the DynamoDB table. The function first parses the
event body to extract the webhook details, including the webhook type, subject, display name,
template file ID, and other optional fields. The function then increments the total count for the
webhook type and generates a webhook ID and URL. The webhook details are saved to the DynamoDB
table using the WebhookRepository class. If the operation is successful, the function returns a
200 response with the webhook ID, URL, type, and creation timestamp and if errors occur during
the execution, the function logs the error and returns a 500 response.
"""
import json
import logging
import os
import uuid
from decimal import Decimal

from time_util import get_current_utc_time
from webhook_repository import WebhookRepository
from webhook_total_count_repository import WebhookIncrementCountRepository
from webhook_type_enum import WebhookType

# dynamodb = boto3.resource("dynamodb")
# main_table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

trigger_webhook_api_endpoint = os.getenv("TRIGGER_WEBHOOK_API_ENDPOINT")

webhook_repository = WebhookRepository()
webhook_increment_count_repository = WebhookIncrementCountRepository()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DecimalEncoder(json.JSONEncoder):
    """ Custom JSON encoder to handle Decimal types """
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

def lambda_handler(event, context): # pylint: disable=unused-argument
    """ Lambda function handler to create a new webhook """
    try:
        # Parse the event body
        data = json.loads(event['body'])

        try:
            webhook_type_enum = WebhookType(data.get("webhook_type").lower())
        except ValueError:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "status": "FAILED",
                        "message": f"Invalid webhook_type. Must be one of {[e.value for e in WebhookType]}."
                    }
                )
            }
        webhook_type = webhook_type_enum.value

        # Increment the total count and get the new sequence_number
        sequence_number = webhook_increment_count_repository.increment_total_count(webhook_type)

        # Generate webhook ID and URL
        webhook_id = str(uuid.uuid4())
        webhook_url = f"{trigger_webhook_api_endpoint}/{webhook_id}"

        # Use time_util to get current time
        created_at = get_current_utc_time()

        # Prepare the DynamoDB item
        item = {
            "webhook_type": webhook_type,
            "sequence_number": sequence_number,
            "webhook_id": webhook_id,
            "webhook_url": webhook_url,
            "created_at": created_at,
            "subject": data.get("subject"),
            "display_name": data.get("display_name"),
            "template_file_id": data.get("template_file_id"),
            "is_generate_certificate": data.get("is_generate_certificate", False),
            "reply_to": data.get("reply_to"),
            "sender_local_part": data.get("sender_local_part"),
            "attachment_file_ids": data.get("attachment_file_ids", []),
            "bcc": data.get("bcc", []),
            "cc": data.get("cc", []),
            "surveycake_link": data.get("surveycake_link"),
            "hash_key": data.get("hash_key"),
            "iv_key": data.get("iv_key"),
            "webhook_name": data.get("webhook_name"),
        }

        # Save the item to the main table
        logger.info("Attempting to put item into DynamoDB: %s", item)
        response = webhook_repository.save_data(item)
        logger.info("DynamoDB put_item response: %s", response)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "status": "SUCCESS",
                    "message": "Webhook successfully created.",
                    "webhook_id": webhook_id,
                    "webhook_url": webhook_url,
                    "webhook_type": webhook_type,
                    # "sequence_number": sequence_number,
                    "created_at": created_at
                }, cls=DecimalEncoder),
        }
    except Exception as e: # pylint: disable=broad-except
        logger.error("Error occurred: %s", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"message": str(e)})
        }
    
