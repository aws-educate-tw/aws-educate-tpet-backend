import logging
import os

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


ENVIRONMENT = os.getenv("ENVIRONMENT")
FILE_SERVICE_API_BASE_URL = (
    f"https://{ENVIRONMENT}-file-service-internal-api-tpet.aws-educate.tw/{ENVIRONMENT}"
)


def get_file_info(file_id):
    try:
        api_url = f"{FILE_SERVICE_API_BASE_URL}/files/{file_id}"
        response = requests.get(url=api_url, timeout=25)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.error("Request timed out for file_id: %s", file_id)
        raise
    except RequestException as e:
        logger.error("Error in get_file_info: %s", e)
        raise
