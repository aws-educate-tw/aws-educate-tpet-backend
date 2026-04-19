import logging
import os

import requests

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RSVPService:
    def __init__(self):
        environment = os.environ.get("ENVIRONMENT")
        self.base_url = f"https://{environment}-rsvp-service-internal-api-tpet.aws-educate.tw/{environment}"

    def verify_campaign(self, campaign_id):
        """Verify the validity of a campaign ID by calling the RSVP service API."""
        try:
            url = f"{self.base_url}/rsvp-service/internal/campaign/{campaign_id}/check"
            response = requests.get(url, timeout=29)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("Request timed out for campaign_id: %s", campaign_id)
            raise
        except requests.exceptions.RequestException as e:
            logger.error("Error in verify_campaign: %s", e)
            raise
