import logging
import os

import requests

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AuthService:
    def __init__(self):
        environment = os.environ.get("ENVIRONMENT")
        domain_name = os.getenv("DOMAIN_NAME")
        self.base_url = f"https://{environment}-auth-service-internal-api-tpet.{domain_name}/{environment}"

    def get_me(self, access_token, timeout=10):
        """
        Retrieve the current authenticated user's information using the provided JWT access token.

        Args:
            access_token (str): The JWT access token for authentication.
            timeout (int, optional): Timeout for the HTTP request in seconds. Defaults to 10.

            dict: A dictionary containing user information if the request is successful,
                  or an error message if an exception occurs.

        Raises:
            None: All exceptions are handled internally and logged.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(
                f"{self.base_url}/auth/users/me", headers=headers, timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error("HTTP error occurred: %s", http_err)
            return {"message": "HTTP error occurred"}
        except requests.exceptions.RequestException as err:
            logger.error("Request error occurred: %s", err)
            return {"message": "Request error occurred"}
