"""
This module contains the WebhookHandler class which is 
responsible for handling the webhook processing.
"""

import base64
import json
import logging
from typing import Any
from urllib.parse import parse_qs

import boto3
import requests
from config import Config
from utils import CryptoHandler, SecretsManager

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ALLOWED_USER_AGENTS = ["GuzzleHttp/7"]

class WebhookHandler:
    """ Class to handle the webhook processing """
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(Config.DYNAMODB_TABLE)
        self.secrets_manager = SecretsManager()
        self.crypto_handler = CryptoHandler()

    def process_request_body(
        self, body: str, is_base64_encoded: bool
    ) -> tuple[str, str]:
        """ Process the request body and extract the svid and hash values """
        if body is None:
            raise ValueError("No body in the request")

        decoded_str = (
            base64.b64decode(body).decode("utf-8") if is_base64_encoded else body
        )
        params = parse_qs(decoded_str)

        svid_value = params.get("svid", [None])[0]
        hash_value = params.get("hash", [None])[0]

        if not svid_value or not hash_value:
            raise ValueError("Missing svid or hash in the request")

        return svid_value, hash_value

    def get_surveycake_data(self, svid_value: str, hash_value: str) -> bytes:
        """ Get the surveycake data from the SurveyCake API """
        api_url = f"https://www.surveycake.com/webhook/v0/{svid_value}/{hash_value}"
        response = requests.get(api_url)

        if response.status_code != 200:
            raise ValueError("Failed to retrieve data from the API")

        return base64.b64decode(response.content)

    def extract_recipient_email(self, answer_data: dict[str, Any]) -> str | None:
        """
        Extract the email address from the surveycake.
        CAUTION: There should be a question containing "信箱" or "email" in one of the surveycake questions.
        """
        for item in answer_data["result"]:
            if "信箱" in item["subject"] or "email" in item["subject"].lower():
                return item["answer"][0]
        return None

    def send_email(self, email_body: dict[str, Any]) -> dict[str, Any]:
        """ Send an email using the send email API """
        try:
            access_token = self.secrets_manager.get_access_token("surveycake")
            logger.info("Send email API endpoint: %s", Config.SEND_EMAIL_API_ENDPOINT)

            response = requests.post(
                Config.SEND_EMAIL_API_ENDPOINT,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                },
                json=email_body,
            )
            logger.info("Send email response: %s", response.json())

            return {"statusCode": response.status_code, "body": response.json()}
        
        except Exception as e:
            logger.error("Failed to send email: %s", str(e))
            return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    def prepare_email_body(
        self, webhook_details: dict[str, Any], recipient_email: str
    ) -> dict[str, Any]:
        """ Prepare the email body for sending the email """
        attachment_file_ids = webhook_details.get("attachment_file_ids", [])
        attachment_file_ids = [item for item in attachment_file_ids if item.strip()]

        if not attachment_file_ids:
            attachment_file_ids = []

        return {
            "recipient_source": "DIRECT",
            "subject": webhook_details["subject"],
            "display_name": webhook_details["display_name"],
            "template_file_id": webhook_details["template_file_id"],
            "attachment_file_ids": attachment_file_ids,
            "is_generate_certificate": webhook_details["is_generate_certificate"],
            "reply_to": webhook_details["reply_to"],
            "sender_local_part": webhook_details["sender_local_part"],
            "bcc": webhook_details["bcc"],
            "cc": webhook_details["cc"],
            "recipients": [{"email": recipient_email, "template_variables": {}}],
        }

    def check_headers_agent(self, headers: dict[str, str]) -> bool:
        """ Check if the User-Agent is allowed """
        allowed_user_agents = ALLOWED_USER_AGENTS
        user_agent = headers.get("User-Agent")

        if user_agent not in allowed_user_agents:
            logger.warning("Unauthorized User-Agent: %s", user_agent)
            return False
        return True

