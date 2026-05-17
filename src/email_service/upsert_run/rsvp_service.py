import logging
import os

import requests

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RSVPService:
    def __init__(self):
        self.environment = os.environ.get("ENVIRONMENT")
        self.base_url = (
            f"https://{self.environment}-rsvp-service-internal-api-tpet.aws-educate.tw"
        )

    def upsert_run_configuration(
        self,
        campaign_id: str,
        run_id: str,
        max_participants: int,
        registration_deadline: str | None = None,
        is_active: bool = True,
    ) -> dict:
        """Upsert run configuration by calling the RSVP service API.

        Args:
            campaign_id: Campaign ID
            run_id: Run ID
            max_participants: Maximum number of participants
            registration_deadline: Registration deadline (ISO 8601 timestamp, optional)
            is_active: Whether the campaign run is active (default: True)

        Returns:
            Response JSON from the RSVP service
        """
        try:
            # Construct composite path parameter: {campaign_id}_{run_id}
            composite_param = f"{campaign_id}_{run_id}"
            url = f"{self.base_url}/rsvp-service/{self.environment}/internal/campaign-runs/{composite_param}"

            # Prepare request body
            body = {
                "registration_deadline": registration_deadline,
                "max_participants": max_participants,
                "is_active": is_active,
            }

            logger.info(
                "Calling RSVP service upsert_run_configuration: campaign_id=%s, run_id=%s",
                campaign_id,
                run_id,
            )

            response = requests.put(url, json=body, timeout=29)
            response.raise_for_status()

            logger.info(
                "Successfully upserted run configuration: campaign_id=%s, run_id=%s",
                campaign_id,
                run_id,
            )

            return response.json()
        except requests.exceptions.Timeout:
            logger.error(
                "Request timed out for campaign_id: %s, run_id: %s",
                campaign_id,
                run_id,
            )
            raise
        except requests.exceptions.RequestException as e:
            logger.error(
                "Error in upsert_run_configuration: %s (campaign_id=%s, run_id=%s)",
                e,
                campaign_id,
                run_id,
            )
            raise
