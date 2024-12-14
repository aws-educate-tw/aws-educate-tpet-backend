import json
import logging
import os
import uuid
from decimal import Decimal

import boto3
from time_util import get_current_utc_time

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))
trigger_webhook_api_endpoint = os.getenv("TRIGGER_WEBHOOK_API_ENDPOINT")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

def lambda_handler(event, context):
    try:
        # Parse the event body
        data = json.loads(event['body'])

        # Generate webhook ID and URL
        webhook_id = str(uuid.uuid4())
        webhook_url = f"{trigger_webhook_api_endpoint}/{webhook_id}"

        # Use time_util to get current time
        created_at = get_current_utc_time()

        # Prepare the DynamoDB item
        item = {
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
            "webhook_name": data.get("webhook_name")
        }

        logger.info("Attempting to put item into DynamoDB: %s", item)
        response = table.put_item(Item=item)
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
                    "created_at": created_at 
                }, cls=DecimalEncoder),
        }
    except Exception as e:
        logger.error("Error occurred: %s", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"message": str(e)})
        }