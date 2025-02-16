import json
import logging
from typing import Any

import requests
from config import Config
from utils import SecretsManager

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

RECIPIENT_SOURCE = "DIRECT"


class EmailService:
    """Class to handle email service operations"""

    def __init__(self):
        self.secrets_manager = SecretsManager()

    def prepare_email_body(
        self, webhook_details: dict[str, Any], recipient_email: str
    ) -> dict[str, Any]:
        """Prepare the email body for sending the email"""
        attachment_file_ids = [
            item
            for item in webhook_details.get("attachment_file_ids", [])
            if item and item.strip()
        ]

        return {
            "recipient_source": RECIPIENT_SOURCE,
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

    def send_email(self, email_body: dict[str, Any]) -> dict[str, Any]:
        """Send an email using the send email API"""
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
                timeout=20,
            )
            logger.info("Send email response: %s", response.json())

            return {"statusCode": response.status_code, "body": response.json()}

        except Exception as e:
            logger.error("Failed to send email: %s", str(e))
            return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
