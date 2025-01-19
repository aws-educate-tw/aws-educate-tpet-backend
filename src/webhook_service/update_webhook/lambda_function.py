"""
"""

import json
import logging
from decimal import Decimal
from typing import Dict

from webhook_repository import WebhookRepository

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
    webhook_id = event.get("pathParameters", {}).get("webhook_id")
    logger.info(f"Received event with webhook_id: {webhook_id}")

    data = json.loads(event['body'])
    logger.info(f"Received data: {data}")

    attributes = webhook_repository.update_data(webhook_id, data)

    return {
        "statusCode": 200,
        "body": json.dumps(attributes, cls=DecimalEncoder, ensure_ascii=False)
    }