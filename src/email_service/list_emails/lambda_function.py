import json
import logging
import math  # Added
from decimal import Decimal

from botocore.exceptions import ClientError
from email_repository import EmailRepository

# Removed EmailServicePaginationStateRepository, decode_key, encode_key, get_current_utc_time

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects."""

    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def extract_query_params(event: dict[str, any]) -> dict[str, any]:
    """Extract query parameters from the API Gateway event."""
    query_params = event.get("queryStringParameters") or {}
    try:
        limit = int(query_params.get("limit", 10))
        page = int(query_params.get("page", 1))
        status = query_params.get("status", None)
        sort_by = query_params.get("sort_by", "created_at")
        sort_order = query_params.get("sort_order", "DESC").upper()
        if sort_order not in ["ASC", "DESC"]:
            sort_order = "DESC"

    except ValueError as e:
        logger.error("Invalid query parameter: %s", e)
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid query parameter: " + str(e)}),
        }

    # Log the extracted parameters
    logger.info(
        "Extracted parameters - limit: %d, page: %d, status: %s, sort_by: %s, sort_order: %s",
        limit,
        page,
        status,
        sort_by,
        sort_order,
    )

    return {
        "limit": limit,
        "page": page,
        "status": status,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }


def lambda_handler(event: dict[str, any], context: object) -> dict[str, any]:
    """Lambda function handler for listing emails."""
    aws_request_id = context.aws_request_id

    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    extracted_params = extract_query_params(event)
    if isinstance(extracted_params, dict) and extracted_params.get("statusCode"):
        return extracted_params

    limit: int = extracted_params["limit"]
    page: int = extracted_params["page"]
    status: str | None = extracted_params["status"]
    sort_by: str = extracted_params["sort_by"]
    sort_order: str = extracted_params["sort_order"]

    path_parameters = event.get("pathParameters", {})
    run_id: str | None = path_parameters.get("run_id")

    if not run_id:
        logger.error("Missing run_id in path parameters")
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Missing run_id in path parameters"}),
        }

    email_repo = EmailRepository()

    filter_criteria = {
        "run_id": run_id,  # run_id is now mandatory
        "page": page,
        "limit": limit,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }
    if status:
        filter_criteria["status"] = status

    try:
        logger.info("Fetching emails with criteria: %s", filter_criteria)
        emails = email_repo.list_emails(filter_criteria)
        # Create a copy of filter_criteria for count_emails, removing pagination params
        count_filter_criteria = filter_criteria.copy()
        count_filter_criteria.pop("page", None)
        count_filter_criteria.pop("limit", None)
        count_filter_criteria.pop("sort_by", None)
        count_filter_criteria.pop("sort_order", None)
        total_items = email_repo.count_emails(count_filter_criteria)

        logger.info(
            "Query successful, %d emails fetched, %d total items.",
            len(emails),
            total_items,
        )

    except ClientError as e:
        logger.error("Query failed: %s", e)
        return {
            "statusCode": 500,  # Changed to 500 for server-side errors
            "body": json.dumps(
                {
                    "message": f"Error querying emails: {e} Request Id: {aws_request_id}",
                }
            ),
        }
    except Exception as e:
        logger.error("An unexpected error occurred: %s", e)
        return {
            "statusCode": 500,  # Changed to 500
            "body": json.dumps(
                {
                    "message": f"An unexpected error occurred: {e} Request Id: {aws_request_id}",
                }
            ),
        }

    # Process emails for Decimal conversion
    processed_emails = []
    for email in emails:
        processed_email = {}
        for key, value in email.items():
            if isinstance(value, Decimal):
                processed_email[key] = float(value)
            else:
                processed_email[key] = value
        processed_emails.append(processed_email)

    total_pages = math.ceil(total_items / limit) if limit > 0 and total_items > 0 else 0
    if total_items == 0:  # if no items, then 0 pages.
        total_pages = 0
    if (
        total_pages == 0 and total_items > 0 and limit > 0
    ):  # if items exist but limit makes total_pages 0, set to 1
        total_pages = 1

    has_next_page = page < total_pages
    has_previous_page = (
        page > 1 and page <= total_pages
    )  # page > total_pages should not happen with correct total_pages

    result = {
        "data": processed_emails,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next_page": has_next_page,
            "has_previous_page": has_previous_page,
        },
    }

    logger.info(
        "Returning response with %d emails, page %d of %d. Total items: %d",
        len(processed_emails),
        page,
        total_pages,
        total_items,
    )
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(result, cls=DecimalEncoder),
    }
