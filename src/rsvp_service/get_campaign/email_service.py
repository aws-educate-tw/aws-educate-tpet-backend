import json
import logging
import os
import time
from urllib import parse, request
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)


class EmailService:
    """Service class for interacting with the email service API."""

    def __init__(self, authorization_header=None):
        environment = os.getenv("ENVIRONMENT")
        domain_name = os.getenv("DOMAIN_NAME")
        self.base_url = f"https://{environment}-email-service-internal-api-tpet.{domain_name}/{environment}"
        self.authorization_header = authorization_header

    def fetch_campaign_runs(self, campaign_id, max_retries=4, initial_retry_delay=2):
        """Fetch all runs for a campaign with retry logic and pagination."""
        runs = []
        page = 1

        while True:
            query = parse.urlencode(
                {
                    "campaign_id": campaign_id,
                    "run_type": "RSVP",
                    "page": page,
                    "limit": 100,
                }
            )
            url = f"{self.base_url}/runs?{query}"

            request_headers = {"Content-Type": "application/json"}
            if self.authorization_header:
                request_headers["authorization"] = self.authorization_header

            req = request.Request(url, headers=request_headers, method="GET")

            for attempt in range(max_retries):
                try:
                    with request.urlopen(req, timeout=10) as response:
                        body = response.read().decode("utf-8")
                        payload = json.loads(body)
                    break
                except HTTPError as error:
                    if attempt < max_retries - 1:
                        retry_delay = initial_retry_delay * (2**attempt)
                        logger.warning(
                            "Attempt %d/%d failed with HTTP %d. Retrying in %d seconds...",
                            attempt + 1,
                            max_retries,
                            error.code,
                            retry_delay,
                        )
                        time.sleep(retry_delay)
                    else:
                        logger.error(
                            "Failed to fetch runs after %d attempts. Last error: HTTP %d",
                            max_retries,
                            error.code,
                        )
                        raise
                except (URLError, TimeoutError) as error:
                    if attempt < max_retries - 1:
                        retry_delay = initial_retry_delay * (2**attempt)
                        logger.warning(
                            "Attempt %d/%d failed due to network issue: %s. Retrying in %d seconds...",
                            attempt + 1,
                            max_retries,
                            error,
                            retry_delay,
                        )
                        time.sleep(retry_delay)
                    else:
                        logger.error(
                            "Failed to fetch runs after %d attempts: %s",
                            max_retries,
                            error,
                        )
                        raise

            data = payload.get("data", [])
            runs.extend(data)

            pagination = payload.get("pagination", {})
            total_pages = int(pagination.get("total_pages", 1) or 1)
            if page >= total_pages:
                break
            page += 1

        return runs
