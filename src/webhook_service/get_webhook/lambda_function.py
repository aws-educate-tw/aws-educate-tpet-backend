import json
import os
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


def lambda_handler(event, context):
    webhook_id = event["pathParameters"]["webhook_id"]
    response = table.get_item(Key={"webhook_id": webhook_id})
    print(response)

    if "Item" not in response:
        return {
            "statusCode": 404, 
            "body": json.dumps({"message": "Webhook not found"})
        }

    file_item = response["Item"]

    data = {
        "subject": file_item["subject"],
        "display_name": file_item["display_name"],
        "template_file_id": file_item["template_file_id"],
        "is_generate_certificate": file_item["is_generate_certificate"],
        "reply_to": file_item["reply_to"],
        "sender_local_part": file_item["sender_local_part"],
        "attachment_file_ids": file_item["attachment_file_ids"],
        "bcc": file_item["bcc"],
        "cc": file_item["cc"],
        "surveycake_link": file_item["surveycake_link"],
        "hask_key": file_item["hask_key"],
        "iv_key": file_item["iv_key"],
        "webhook_name": file_item["webhook_name"]
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
