import logging
import os

import requests

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AuthService:
    def __init__(self):
        environment = os.environ.get("ENVIRONMENT")
        self.base_url = f"https://{environment}-auth-service-internal-api-tpet.aws-educate.tw/{environment}"

    def get_me(self, access_token):
        """
        Retrieve the current user's information using the provided JWT token.

        Parameters:
        access_token (str): JWT token

        Returns:
        dict: User information or error message
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(f"{self.base_url}/auth/users/me", headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error("HTTP error occurred: %s", http_err)
            return {"message": "HTTP error occurred"}
        except requests.exceptions.RequestException as err:
            logger.error("Request error occurred: %s", err)
            return {"message": "Request error occurred"}
