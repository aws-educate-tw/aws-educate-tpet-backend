import logging
import os

import requests

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class EmailService:
    def __init__(self):
        environment = os.environ.get("ENVIRONMENT")
        domain_name = os.getenv("DOMAIN_NAME")
        self.base_url = f"https://{environment}-email-service-internal-api-tpet.{domain_name}/{environment}"

    def create_run(
        self,
        run_type,
        recipient_source,
        access_token,
        timeout=10,
    ):
        """
        Creates a new run in the email service.

        Args:
            run_type (str): The type of run (e.g., 'WEBHOOK').
            recipient_source (str): The source of recipients (e.g., 'DIRECT').
            access_token (str): JWT token for authorization (optional).
            timeout (int, optional): Request timeout in seconds. Defaults to 10.

        Returns:
            dict: The response from the email service API.

        Raises:
            requests.exceptions.Timeout: If the request times out.
            requests.exceptions.RequestException: For other request-related errors.
        """
        url = f"{self.base_url}/runs"
        headers = {"Content-Type": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        data = {"run_type": run_type, "recipient_source": recipient_source}
        try:
            response = requests.post(url, json=data, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("Request timed out when creating run: %s", data)
            raise
        except requests.exceptions.RequestException as e:
            logger.error("Error in create_run: %s", e)
            raise
