import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from urllib.error import HTTPError, URLError

from campaign_repository import CampaignRepository
from campaign_run_repository import CampaignRunRepository
from participant_repository import ParticipantRepository

from email_service import EmailService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects."""

    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def _response(status_code, body):
    """Build a standardized API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def _to_int(value, default_value=0):
    """Convert a value to integer"""
    try:
        if value is None:
            return default_value
        return int(value)
    except (TypeError, ValueError):
        return default_value


def _extract_auth_header(headers):
    """Extract the authorization token from request headers."""
    if not headers:
        return None

    return headers.get("authorization") or headers.get("Authorization")


def _safe_event_log_fields(event):
    """Extract non-sensitive event metadata for logging."""
    request_context = event.get("requestContext") or {}
    http_context = request_context.get("http") or {}

    return {
        "action": event.get("action"),
        "path": event.get("path") or http_context.get("path"),
        "httpMethod": event.get("httpMethod") or http_context.get("method"),
        "requestId": request_context.get("requestId"),
    }


def _get_campaign_runs(
    email_service, campaign_id, max_retries=4, initial_retry_delay=2
):
    """Get all runs for a campaign with retry logic and pagination."""
    runs = []
    page = 1

    while True:
        for attempt in range(max_retries):
            try:
                payload = email_service.list_runs(
                    campaign_id=campaign_id, run_type="RSVP", page=page, limit=100
                )
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
                        "Failed to get runs after %d attempts. Last error: HTTP %d",
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
                        "Failed to get runs after %d attempts: %s",
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


def lambda_handler(event: dict[str, any], context: object) -> dict[str, any]:
    """Lambda function handler for retrieving campaign details with runs and participants."""
    aws_request_id = getattr(context, "aws_request_id", None)
    logger.info("Received event metadata: %s", _safe_event_log_fields(event))

    if event.get("action") == "PREWARM":
        logger.info(
            "Received a prewarm request. Skipping business logic. Request ID: %s",
            aws_request_id,
        )
        return {"statusCode": 200, "body": "Successfully warmed up"}

    campaign_id = event.get("pathParameters", {}).get("campaign_id")
    campaign_repository = CampaignRepository()
    campaign_run_repository = CampaignRunRepository()
    participant_repository = ParticipantRepository()

    try:
        campaign_item = campaign_repository.get_campaign_by_id(campaign_id)
        if not campaign_item:
            return _response(
                404,
                {
                    "message": f"Campaign with ID '{campaign_id}' not found",
                },
            )

        authorization_header = _extract_auth_header(event.get("headers", {}))

        # Step 1: Get run_id and subject from GET /runs with RSVP + campaign_id
        email_service = EmailService(authorization_header)
        run_items_from_email_service = _get_campaign_runs(email_service, campaign_id)

        # Step 2: Query campaign run for registration_deadline and is_active
        campaign_run_items = campaign_run_repository.query_by_campaign_id(campaign_id)

        campaign_run_by_run_id = {
            item.get("run_id"): item
            for item in campaign_run_items
            if item.get("run_id")
        }

        # Step 3: Query participants for each run in parallel
        runs_with_participants = {}
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(
                    participant_repository.query_by_run_id, run_item.get("run_id")
                ): run_item.get("run_id")
                for run_item in run_items_from_email_service
                if run_item.get("run_id")
            }

            for future in as_completed(futures):
                run_id = futures[future]
                runs_with_participants[run_id] = {"participants": future.result()}

        # Step 4: Merge run data with configurations and participant statistics
        runs = []
        for run_item in run_items_from_email_service:
            run_id = run_item.get("run_id")
            campaign_run_item = campaign_run_by_run_id.get(run_id, {})
            participants_info = runs_with_participants.get(run_id, {"participants": []})

            runs.append(
                {
                    "run_id": run_id,
                    "subject": run_item.get("subject"),
                    "registration_deadline": campaign_run_item.get(
                        "registration_deadline"
                    ),
                    "max_participants": _to_int(
                        campaign_run_item.get("max_participants")
                    ),
                    "is_active": bool(campaign_run_item.get("is_active", False)),
                    "participants": participants_info["participants"],
                }
            )

        response_body = {
            "campaign_id": campaign_item.get("campaign_id"),
            "campaign_name": campaign_item.get("campaign_name"),
            "campaign_start_time": campaign_item.get("campaign_start_time"),
            "campaign_end_time": campaign_item.get("campaign_end_time"),
            "campaign_location": campaign_item.get("campaign_location"),
            "campaign_created_at": campaign_item.get("created_at"),
            "is_active": bool(campaign_item.get("is_active")),
            "runs": runs,
        }
        return _response(200, response_body)

    except HTTPError as error:
        logger.warning(
            "Propagating upstream error from email service: HTTP %d", error.code
        )

        error_body = {"message": "Failed to get runs from email service"}
        try:
            response_text = error.read().decode("utf-8", errors="replace")
            if response_text:
                parsed_error = json.loads(response_text)
                if isinstance(parsed_error, dict) and "message" in parsed_error:
                    error_body["message"] = (
                        f"Failed to get runs from email service: {parsed_error['message']}"
                    )
                else:
                    error_body["message"] = (
                        f"Failed to get runs from email service: {response_text}"
                    )
        except Exception:
            logger.exception("Failed to parse error response from email service")

        return _response(error.code, error_body)
    except Exception as error:
        logger.exception("Database error when fetching campaign data: %s", error)
        return _response(
            500,
            {
                "message": "Failed to query campaign data.",
            },
        )
