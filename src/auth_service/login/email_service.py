import logging
import os
import socket
from urllib import error, request

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
            logger.info("Triggering email_service prewarm by calling health endpoint")
            request.urlopen(f"{self.base_url}/email-service/health", timeout=timeout)
        except TimeoutError:
            pass  # Request sent successfully, Aurora is resuming - timeout is expected
        except error.URLError as e:
            if isinstance(e.reason, socket.timeout):
                pass  # Same as above, wrapped by urllib
            else:
                logger.warning("Failed to trigger email_service prewarm: %s", e)
        except Exception as e:
            logger.warning("Failed to trigger email_service prewarm: %s", e)
