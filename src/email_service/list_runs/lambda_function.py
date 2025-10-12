import json
import logging
import math  # Added for math.ceil

from botocore.exceptions import ClientError
from run_repository import RunRepository

# Removed unused time_util import

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DecimalEncoder is removed as RunRepository handles Decimal to float for PostgreSQL JSONB.


def extract_query_params(event: dict[str, any]) -> dict[str, any]:
    """Extract and validate query parameters from the API Gateway event."""
    params = (
        event.get("queryStringParameters")
        if event.get("queryStringParameters") is not None
        else {}
    )

    try:
        page: int = int(params.get("page", 1))
        limit: int = int(
            params.get("limit", 20)
        )  # Default to 20 as per example response
        sort_by: str = params.get("sort_by", "created_at")
        sort_order: str = params.get("sort_order", "DESC").upper()
        run_type: str | None = params.get("run_type", None)
        created_year: str | None = params.get("created_year", None)
        # Add any other filter parameters the user might send, e.g. sender_id
        sender_id: str | None = params.get("sender_id", None)

        if sort_order not in ["ASC", "DESC"]:
            logger.warning(
                "Invalid sort_order '%s' received, defaulting to DESC.", sort_order
            )
            sort_order = "DESC"

        if page < 1:
            logger.warning("Invalid page number %d received, defaulting to 1.", page)
            page = 1

        if limit < 1:
            logger.warning("Invalid limit %d received, defaulting to 20.", limit)
            limit = 20

    except ValueError as e:
        logger.error("Invalid query parameter type: %s", e)
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid query parameter type: " + str(e)}),
        }

    # Log the extracted parameters
    logger.info(
        "Extracted parameters - page: %d, limit: %d, sort_by: %s, sort_order: %s, run_type: %s, created_year: %s, sender_id: %s",
        page,
        limit,
        sort_by,
        sort_order,
        run_type,
        created_year,
        sender_id,
    )

    return {
        "page": page,
        "limit": limit,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "run_type": run_type,
        "created_year": created_year,
        "sender_id": sender_id,  # Include sender_id if it's a filter
    }


def lambda_handler(event: dict[str, any], context: object) -> dict[str, any]:
    """Lambda function handler for listing runs using PostgreSQL."""
    aws_request_id = context.aws_request_id

    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    # Extract and validate query parameters
    query_params_result = extract_query_params(event)
    if isinstance(query_params_result, dict) and query_params_result.get("statusCode"):
        return query_params_result

    # Ensure all expected keys are present, providing defaults if necessary
    page = query_params_result.get("page", 1)
    limit = query_params_result.get("limit", 100)
    sort_by = query_params_result.get("sort_by", "created_at")
    sort_order = query_params_result.get("sort_order", "DESC")
    # Filters for the repository
    filters = {}
    if query_params_result.get("run_type"):
        filters["run_type"] = query_params_result["run_type"]
    if query_params_result.get("created_year"):
        filters["created_year"] = query_params_result["created_year"]
    if query_params_result.get("sender_id"):  # Assuming sender_id is a direct filter
        filters["sender_id"] = query_params_result["sender_id"]

    # Get access token from headers (user_id might be needed for filtering by sender_id if not passed directly)
    # For now, assuming sender_id can be an optional filter from query params.
    # If runs should always be scoped to the current user, this logic would need adjustment.
    authorization_header = event["headers"].get("authorization")
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return {
            "statusCode": 401,
            "body": json.dumps({"message": "Missing or invalid Authorization header"}),
        }
    # access_token = authorization_header.split(" ")[1]
    # user_id = CurrentUserUtil().get_user_id_from_access_token(access_token)
    # If filtering by current user is mandatory, add user_id to filters:
    # filters["sender_id"] = user_id

    run_repo = RunRepository()

    try:
        # Prepare params for repository methods
        repo_params = {
            "page": page,
            "limit": limit,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "filters": filters,  # Pass collected filters
        }

        # Add specific top-level params if your repository expects them directly
        # For example, if run_type and created_year are not part of a 'filters' dict:
        if "run_type" in filters:
            repo_params["run_type"] = filters["run_type"]
        if "created_year" in filters:
            repo_params["created_year"] = filters["created_year"]
        if "sender_id" in filters:
            repo_params["sender_id"] = filters["sender_id"]

        runs = run_repo.list_runs(repo_params)
        total_items = run_repo.count_runs(repo_params)

        logger.info(
            "Query successful. Fetched %d runs. Total items: %d", len(runs), total_items
        )

    except ClientError as e:  # Catch boto3 client errors specifically if needed
        logger.error(
            "Repository query failed (ClientError): %s, Request ID: %s",
            e,
            aws_request_id,
        )
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"message": f"Error querying runs: {e}, Request ID: {aws_request_id}"}
            ),
        }
    except Exception as e:  # Catch other potential errors from repository or logic
        logger.error(
            "Repository query failed (Exception): %s, Request ID: %s", e, aws_request_id
        )
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "message": f"An unexpected error occurred: {e}, Request ID: {aws_request_id}"
                }
            ),
        }

    # Calculate pagination details
    total_pages = math.ceil(total_items / limit) if limit > 0 else 0
    has_next_page = page < total_pages
    has_previous_page = page > 1

    result = {
        "data": runs,  # Assumes runs are already in correct format (e.g., Decimals handled by repo)
        "pagination": {
            "page": page,
            "limit": limit,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next_page": has_next_page,
            "has_previous_page": has_previous_page,
        },
    }

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            # Add CORS headers if needed
            # "Access-Control-Allow-Origin": "*",
            # "Access-Control-Allow-Credentials": True,
        },
        "body": json.dumps(
            result
        ),  # Default json.dumps should be fine if repo returns serializable data
    }
