"""
This lambda function updates an existing webhook in the DynamoDB table.
"""

import json
import logging
from decimal import Decimal
from typing import Dict

from webhook_repository import WebhookRepository
from webhook_type_enum import WebhookType

webhook_repository = WebhookRepository()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DecimalEncoder(json.JSONEncoder):
    """ Custom JSON Encoder to handle Decimal types. """
    def default(self, o):
        if isinstance(o, Decimal):
            # Convert Decimal to float or int, depending on your needs
            return float(o)
        return super(DecimalEncoder, self).default(o)


def lambda_handler(event: Dict, context) -> Dict: # pylint: disable=unused-argument
    """
    Lambda function to fetch data from DynamoDB with optional limit, sort order, and pagination using sequence numbers.
    """

    # Check if the event is a pre-warm request
    if event.get("action") == "PREWARM":  
        logger.info("Received a prewarm request. Skipping business logic.")  
        return {  
            "statusCode": 200,  
            "body": "Successfully warmed up"  
        }  
    
    webhook_id = event.get("pathParameters", {}).get("webhook_id")
    if not webhook_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing webhook_id in path parameters."})
        }
    
    data = json.loads(event['body'])
    if data.get("webhook_type") not in [e.value for e in WebhookType]:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "error": f"Invalid webhook_type. Must be one of {[e.value for e in WebhookType]}."
                }
            )
        }

    try:
        attributes = webhook_repository.update_webhook(webhook_id, data)
        logger.info("Updated webhook attributes: %s", attributes)
    
        return {
            "statusCode": 200,
            "body": json.dumps(attributes, cls=DecimalEncoder, ensure_ascii=False)
        }
    except ValueError as e:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": str(e)})
        }
    except RuntimeError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }