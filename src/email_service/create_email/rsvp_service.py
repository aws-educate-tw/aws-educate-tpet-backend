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

    def import_participant(
        self,
        run_id: str,
        participant_id: str,
        email: str,
        campaign_id: str,
        name: str,
    ) -> dict:
        """Import participant by calling the RSVP service API.

        Args:
            run_id: Run ID
            participant_id: Participant ID requested by caller
            email: Participant email
            campaign_id: Campaign ID
            name: Participant name

        Returns:
            Response JSON from the RSVP service
        """
        try:
            url = f"{self.base_url}/rsvp-service/{self.environment}/internal/runs/{run_id}/participants"

            body = {
                "participant_id": participant_id,
                "email": email,
                "campaign_id": campaign_id,
                "name": name,
            }

            logger.info(
                "Calling RSVP service import_participant: run_id=%s, participant_id=%s, email=%s, campaign_id=%s",
                run_id,
                participant_id,
                email,
                campaign_id,
            )

            response = requests.post(url, json=body, timeout=29)
            response.raise_for_status()

            result = response.json()
            logger.info(
                "Successfully imported participant: run_id=%s, requested_participant_id=%s",
                run_id,
                participant_id,
            )

            return result
        except requests.exceptions.Timeout:
            logger.error(
                "Request timed out for run_id: %s, email: %s",
                run_id,
                email,
            )
            raise
        except requests.exceptions.RequestException as e:
            logger.error(
                "Error in import_participant: %s (run_id=%s, email=%s)",
                e,
                run_id,
                email,
            )
            raise
