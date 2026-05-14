import logging
import os
from urllib import request

ENVIRONMENT = os.getenv("ENVIRONMENT")
DOMAIN_NAME = os.getenv("DOMAIN_NAME")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class EmailService:
    """Service class for interacting with the email service API."""

    def __init__(self):
        self.base_url = f"https://{ENVIRONMENT}-email-service-internal-api-tpet.{DOMAIN_NAME}/{ENVIRONMENT}"

    def health_check(self, timeout: int = 1) -> None:
        """Hit health endpoint to kick off Aurora resume."""
        try:
            request.urlopen(f"{self.base_url}/email-service/health", timeout=timeout)
        except Exception as e:
            logger.warning("Failed to trigger email_service prewarm: %s", e)
