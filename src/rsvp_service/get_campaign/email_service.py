import json
import os
from urllib import parse, request

ENVIRONMENT = os.getenv("ENVIRONMENT")
DOMAIN_NAME = os.getenv("DOMAIN_NAME")


class EmailService:
    """Service class for interacting with the email service API."""

    def __init__(self, authorization_header=None):
        self.base_url = f"https://{ENVIRONMENT}-email-service-internal-api-tpet.{DOMAIN_NAME}/{ENVIRONMENT}"
        self.authorization_header = authorization_header

    def list_runs(self, campaign_id, run_type, page, limit):
        """List runs for a campaign."""
        query = parse.urlencode(
            {
                "campaign_id": campaign_id,
                "run_type": run_type,
                "page": page,
                "limit": limit,
            }
        )
        url = f"{self.base_url}/runs?{query}"

        request_headers = {"Content-Type": "application/json"}
        if self.authorization_header:
            request_headers["authorization"] = self.authorization_header

        req = request.Request(url, headers=request_headers, method="GET")

        with request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)

    def list_emails(self, run_id, page, limit, status=None):
        """List emails for a run."""
        query_params = {
            "page": page,
            "limit": limit,
        }
        if status is not None:
            query_params["status"] = status

        query = parse.urlencode(query_params)
        url = f"{self.base_url}/runs/{run_id}/emails?{query}"

        request_headers = {"Content-Type": "application/json"}
        if self.authorization_header:
            request_headers["authorization"] = self.authorization_header

        req = request.Request(url, headers=request_headers, method="GET")

        with request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
