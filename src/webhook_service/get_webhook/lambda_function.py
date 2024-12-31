import json
import logging
import os
from decimal import Decimal

import boto3
from webhook_repository import WebhookRepository

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

WebhookRepository = WebhookRepository()

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


def lambda_handler(event, context):
    webhook_id = event["pathParameters"]["webhook_id"]
    webhook_details = WebhookRepository.get_item(webhook_id)

    if webhook_details is None:
        return {
            "statusCode": 404, 
            "body": json.dumps({"message": "Webhook not found"})
        }

    webhook_details_item = webhook_details["Item"]

    logger.info("Webhook details: %s", webhook_details_item)

    data = {
        "webhook_id": webhook_details_item["webhook_id"],
        "webhook_url": webhook_details_item["webhook_url"],
        "subject": webhook_details_item["subject"],
        "display_name": webhook_details_item["display_name"],
        "template_file_id": webhook_details_item["template_file_id"],
        "is_generate_certificate": webhook_details_item["is_generate_certificate"],
        "reply_to": webhook_details_item["reply_to"],
        "sender_local_part": webhook_details_item["sender_local_part"],
        "attachment_file_ids": webhook_details_item["attachment_file_ids"],
        "bcc": webhook_details_item["bcc"],
        "cc": webhook_details_item["cc"],
        "surveycake_link": webhook_details_item["surveycake_link"],
        "hash_key": webhook_details_item["hash_key"],
        "iv_key": webhook_details_item["iv_key"],
        "webhook_name": webhook_details_item["webhook_name"],
        "webhook_type": webhook_details_item["webhook_type"],
    }

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
            }, cls=DecimalEncoder),
    }
