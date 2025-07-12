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

# Calculate batch size to avoid RDS Data API 1MB limit
RDS_DATA_API_SAFE_BATCH_SIZE = 500  # Safe limit to avoid 1MB response size


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects."""

    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def extract_query_params(event: dict[str, any]) -> dict[str, any]:
    """Extract query parameters from the API Gateway event."""
    query_params = event.get("queryStringParameters") or {}
    limit_param = query_params.get("limit")  # No default value

    if limit_param is None:
        logger.error("Missing required 'limit' query parameter.")
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "message": "Missing required 'limit' query parameter. Please provide a number (max 5000) or 'ALL'."
                }
            ),
        }

    try:
        # Support limit=ALL
        if isinstance(limit_param, str) and limit_param.upper() == "ALL":
            limit = "ALL"
        else:
            limit = int(limit_param)
            if limit <= 0 or limit > 5000:
                raise ValueError("'limit' must be between 1 and 5000, or 'ALL'.")
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
        "Extracted parameters - limit: %s, page: %d, status: %s, sort_by: %s, sort_order: %s",
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

    limit: int | str = extracted_params["limit"]
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

    # Support limit=ALL: count total items and override pagination
    if limit == "ALL":
        count_filter = {"run_id": run_id}
        if status:
            count_filter["status"] = status
        total_items = email_repo.count_emails(count_filter)  # support count first
        limit = total_items  # override limit for fetching
        page = 1  # reset to first page
        filter_criteria["limit"] = limit
        filter_criteria["page"] = page

    try:
        logger.info("Fetching emails with criteria: %s", filter_criteria)

        requested_limit = limit

        # If requested limit is small, use it directly
        if requested_limit <= RDS_DATA_API_SAFE_BATCH_SIZE:
            emails = email_repo.list_emails(filter_criteria)
            # Handle potential None return from list_emails
            if emails is None:
                emails = []
            logger.info(
                "Single batch query successful, %d emails fetched.", len(emails)
            )
        else:
            # For large requests, use batch fetching
            logger.info(
                "Large request detected (limit=%d), using batch fetching with max batch size %d",
                requested_limit,
                RDS_DATA_API_SAFE_BATCH_SIZE,
            )

            all_emails = []
            current_offset = (
                page - 1
            ) * limit  # Calculate starting offset for the requested page
            remaining_items = requested_limit

            while remaining_items > 0:
                # Calculate current batch size
                current_batch_size = min(RDS_DATA_API_SAFE_BATCH_SIZE, remaining_items)

                # Calculate current page for this batch based on current_offset
                current_page = (current_offset // current_batch_size) + 1

                # Create batch filter criteria
                batch_filter_criteria = filter_criteria.copy()
                batch_filter_criteria["limit"] = current_batch_size
                batch_filter_criteria["page"] = current_page

                logger.info(
                    "Fetching batch: page=%d, limit=%d, offset=%d",
                    current_page,
                    current_batch_size,
                    current_offset,
                )

                # Fetch current batch
                batch_emails = email_repo.list_emails(batch_filter_criteria)

                # Handle potential None return from list_emails
                if batch_emails is None:
                    batch_emails = []

                # If we get less than expected, we've reached the end
                if len(batch_emails) == 0:
                    logger.info("No more emails to fetch, breaking from batch loop")
                    break

                # Add batch results to all_emails
                all_emails.extend(batch_emails)

                # Update counters
                remaining_items -= len(batch_emails)
                current_offset += len(batch_emails)

                # If we got fewer items than batch size, we've reached the end
                if len(batch_emails) < current_batch_size:
                    logger.info(
                        "Reached end of data (got %d items, expected %d)",
                        len(batch_emails),
                        current_batch_size,
                    )
                    break

            emails = all_emails
            logger.info(
                "Batch fetching completed, %d total emails fetched.", len(emails)
            )

        # Get total count for pagination info
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
