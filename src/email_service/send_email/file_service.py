import logging
import os

import requests

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

domain_name = os.getenv("DOMAIN_NAME")
class FileService:
    def __init__(self):
        environment = os.getenv("ENVIRONMENT")
        self.base_url = f"https://{environment}-file-service-internal-api-tpet.{domain_name}/{environment}"

    def get_file_info(self, file_id, access_token):
        """
        Retrieve file information using the provided file ID.

        Parameters:
        file_id (str): The ID of the file
        access_token (str): JWT token for authorization

        Returns:
        dict: File information or raises an exception on error
        """
        api_url = f"{self.base_url}/files/{file_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(url=api_url, headers=headers, timeout=25)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("Request timed out for file_id: %s", file_id)
            raise
        except requests.exceptions.RequestException as e:
            logger.error("Error in get_file_info: %s", e)
            raise
