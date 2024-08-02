import base64
import json
import logging
from decimal import Decimal
from typing import Optional

from botocore.exceptions import ClientError
from current_user_util import CurrentUserUtil
from email_service_pagination_state_repository import (
    EmailServicePaginationStateRepository,
)
from last_evaluated_key_util import decode_key, encode_key
from run_repository import RunRepository
from time_util import get_current_utc_time, get_previous_year

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects."""

    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


def extract_query_params(event: dict[str, any]) -> dict[str, any]:
    """Extract query parameters from the API Gateway event."""
    limit: int = 10
    last_evaluated_key: Optional[str] = None
    sort_order: str = "DESC"
    created_year: Optional[str] = None

    # Extract query parameters if they exist
    if event.get("queryStringParameters"):
        try:
            limit = int(event["queryStringParameters"].get("limit", 10))
            last_evaluated_key = event["queryStringParameters"].get(
                "last_evaluated_key", None
            )
            sort_order = event["queryStringParameters"].get("sort_order", "DESC")
            created_year = event["queryStringParameters"].get("created_year", None)
        except ValueError as e:
            logger.error("Invalid query parameter: %s", e)
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Invalid query parameter: " + str(e)}),
            }

    # Log the extracted parameters
    logger.info(
        "Extracted parameters - limit: %d, last_evaluated_key: %s, sort_order: %s, created_year: %s",
        limit,
        last_evaluated_key,
        sort_order,
        created_year,
    )

    return {
        "limit": limit,
        "last_evaluated_key": last_evaluated_key,
        "sort_order": sort_order,
        "created_year": created_year,
    }


def lambda_handler(event: dict[str, any], context: object) -> dict[str, any]:
    """Lambda function handler for listing runs."""
    extracted_params = extract_query_params(event)
    if isinstance(extracted_params, dict) and extracted_params.get("statusCode"):
        return extracted_params

    limit: int = extracted_params["limit"]
    last_evaluated_key: Optional[str] = extracted_params["last_evaluated_key"]
    sort_order: str = extracted_params["sort_order"]
    created_year: Optional[str] = extracted_params["created_year"]

    index_name = "created_year-created_at-gsi"

    # Get access token from headers and retrieve user_id
    authorization_header = event["headers"].get("authorization")
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return {
            "statusCode": 401,
            "body": json.dumps({"message": "Missing or invalid Authorization header"}),
        }
    access_token = authorization_header.split(" ")[1]
    user_id = CurrentUserUtil().get_user_id_from_access_token(access_token)

    # Init dynamoDB entities
    run_repo = RunRepository()
    pagination_state_repo = EmailServicePaginationStateRepository()

    if last_evaluated_key:
        try:
            # Decode the base64 last_evaluated_key
            current_last_evaluated_key = last_evaluated_key
            last_evaluated_key = decode_key(last_evaluated_key)
            logger.info("Decoded last_evaluated_key: %s", last_evaluated_key)
        except ValueError as e:
            logger.error("Invalid last_evaluated_key format: %s", e)
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "message": "Invalid last_evaluated_key format. It must be a valid base64 encoded JSON string."
                    }
                ),
            }
    else:
        current_last_evaluated_key = None
        # Clear old pagination state if no last_evaluated_key is provided
        pagination_state_repo.save_pagination_state(
            {
                "user_id": user_id,
                "index_name": index_name,
                "last_evaluated_keys": [],
                "created_at": get_current_utc_time(),
                "updated_at": get_current_utc_time(),
                "limit": limit,
            }
        )

    # Default to current and previous year for querying if created_year is not provided
    if created_year:
        years_to_query = [created_year]
    else:
        current_year = get_current_utc_time()[:4]
        previous_year = get_previous_year(current_year)
        years_to_query = [current_year, previous_year]

    runs = []

    # Query the table using the provided parameters
    try:
        for year in years_to_query:
            while True:
                response = run_repo.query_runs_by_created_year_and_created_at_gsi(
                    year, limit - len(runs), last_evaluated_key, sort_order
                )
                runs.extend(response.get("Items", []))
                last_evaluated_key = response.get("LastEvaluatedKey")

                if last_evaluated_key is None or len(runs) >= limit:
                    break

            if len(runs) >= limit:
                break

        next_last_evaluated_key = response.get("LastEvaluatedKey")

        logger.info("Query successful")
    except ClientError as e:
        logger.error("Query failed: %s", e)
        return {"statusCode": 400, "body": json.dumps({"message": str(e)})}

    # Encode last_evaluated_key to base64 if it's not null
    if next_last_evaluated_key:
        next_last_evaluated_key = encode_key(next_last_evaluated_key)

    # Store the pagination state for the next request
    pagination_state = (
        pagination_state_repo.get_pagination_state_by_user_id_and_index_name(
            user_id, index_name
        )
    )
    last_evaluated_keys = pagination_state.get("last_evaluated_keys", [])

    # Append the next_last_evaluated_key only if it is not already in the list
    if next_last_evaluated_key and next_last_evaluated_key not in last_evaluated_keys:
        last_evaluated_keys.append(next_last_evaluated_key)

    pagination_state_repo.save_pagination_state(
        {
            "user_id": user_id,
            "index_name": index_name,
            "last_evaluated_keys": last_evaluated_keys,
            "created_at": pagination_state.get("created_at", get_current_utc_time()),
            "updated_at": get_current_utc_time(),
            "limit": limit,
        }
    )

    # Sort the results by created_at
    reverse_order = True if sort_order.upper() == "DESC" else False
    runs.sort(key=lambda x: x.get("created_at", ""), reverse=reverse_order)

    # Encode last_evaluated_key to base64 if it's not null
    for run in runs:
        for key, value in run.items():
            if isinstance(value, Decimal):
                run[key] = float(value)

    # Find the index of the current_last_evaluated_key in last_evaluated_keys
    if current_last_evaluated_key in last_evaluated_keys:
        current_index = last_evaluated_keys.index(current_last_evaluated_key)
        previous_last_evaluated_key = (
            last_evaluated_keys[current_index - 1] if current_index > 0 else None
        )
    else:
        previous_last_evaluated_key = None

    result = {
        "data": runs[:limit],
        "previous_last_evaluated_key": previous_last_evaluated_key,
        "current_last_evaluated_key": current_last_evaluated_key,
        "next_last_evaluated_key": next_last_evaluated_key,
    }

    logger.info("Returning response with %d runs", len(runs))
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(result, cls=DecimalEncoder),
    }
