"""
This module contains the repository for fetching from a table named webhook in DynamoDB.
"""
import json
import logging
import os

import boto3  # type: ignore # pylint: disable=import-error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class WebhookRepository:
    """ Repository for fetching webhooks from DynamoDB. """
    def __init__(self):
        """
        Initialize the repository with the DynamoDB table.
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

    def update_data(self, webhook_id: str, data: dict):
        """
        Update the webhook item in DynamoDB.
        """
        try:
            response = self.table.update_item(
                Key={ 
                    "webhook_id": webhook_id
                },
                UpdateExpression="""
                    set subject=:subject, 
                        display_name=:display_name, 
                        template_file_id=:template_file_id, 
                        is_generate_certificate=:is_generate_certificate, 
                        reply_to=:reply_to, 
                        sender_local_part=:sender_local_part, 
                        attachment_file_ids=:attachment_file_ids, 
                        bcc=:bcc, 
                        cc=:cc, 
                        surveycake_link=:surveycake_link, 
                        hash_key=:hash_key, 
                        iv_key=:iv_key, 
                        webhook_name=:webhook_name, 
                        webhook_type=:webhook_type
                """,
                ExpressionAttributeValues={
                    ":subject": data.get("subject"),
                    ":display_name": data.get("display_name"),
                    ":template_file_id": data.get("template_file_id"),
                    ":is_generate_certificate": data.get("is_generate_certificate"),
                    ":reply_to": data.get("reply_to"),
                    ":sender_local_part": data.get("sender_local_part"),
                    ":attachment_file_ids": data.get("attachment_file_ids"),
                    ":bcc": data.get("bcc"),
                    ":cc": data.get("cc"),
                    ":surveycake_link": data.get("surveycake_link"),
                    ":hash_key": data.get("hash_key"),
                    ":iv_key": data.get("iv_key"),
                    ":webhook_name": data.get("webhook_name"),
                    ":webhook_type": data.get("webhook_type"),
                    ":webhook_id": webhook_id
                },
                ConditionExpression="webhook_id = :webhook_id",
                ReturnValues="ALL_NEW"
            )
            attributes = response.get("Attributes", {})
            logger.info("Updated attributes: %s", attributes)

            return attributes
        except Exception as e:
            logger.error(
                "Error updating webhook with ID: %s. Error: %s",
                webhook_id,
                str(e)
            )
            return None