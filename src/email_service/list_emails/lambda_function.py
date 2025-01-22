import json
import logging
from decimal import Decimal

from botocore.exceptions import ClientError
from current_user_util import CurrentUserUtil
from email_repository import EmailRepository
from email_service_pagination_state_repository import (
    EmailServicePaginationStateRepository,
)
from last_evaluated_key_util import decode_key, encode_key
from time_util import get_current_utc_time

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
    limit: int = 10
    last_evaluated_key: str | None = None
    status: str | None = None
    sort_order: str = "DESC"

    # Extract query parameters if they exist
    if event.get("queryStringParameters"):
        try:
            limit = int(event["queryStringParameters"].get("limit", 10))
            last_evaluated_key = event["queryStringParameters"].get(
                "last_evaluated_key", None
            )
            status = event["queryStringParameters"].get("status", None)
            sort_order = event["queryStringParameters"].get("sort_order", "DESC")
        except ValueError as e:
            logger.error("Invalid query parameter: %s", e)
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Invalid query parameter: " + str(e)}),
            }

    # Log the extracted parameters
    logger.info(
        "Extracted parameters - limit: %d, last_evaluated_key: %s, status: %s, sort_order: %s",
        limit,
        last_evaluated_key,
        status,
        sort_order,
    )

    return {
        "limit": limit,
        "last_evaluated_key": last_evaluated_key,
        "status": status,
        "sort_order": sort_order,
    }


def lambda_handler(event: dict[str, any], context: object) -> dict[str, any]:
    """Lambda function handler for listing emails."""

    # Identify if the incoming event is a prewarm request
    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    extracted_params = extract_query_params(event)
    if isinstance(extracted_params, dict) and extracted_params.get("statusCode"):
        return extracted_params

    limit: int = extracted_params["limit"]
    last_evaluated_key: str | None = extracted_params["last_evaluated_key"]
    status: str | None = extracted_params["status"]
    sort_order: str = extracted_params["sort_order"]
    run_id: str = event["pathParameters"]["run_id"]

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
    email_repo = EmailRepository()
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
                "index_name": (
                    "email-run_id-status-gsi"
                    if status
                    else "email-run_id-created_at-gsi"
                ),
                "last_evaluated_keys": [],
                "created_at": get_current_utc_time(),
                "updated_at": get_current_utc_time(),
                "limit": limit,
            }
        )

    emails = []

    # Query the table using the provided parameters
    try:
        while True:
            if status:
                response = email_repo.query_emails_by_run_id_and_status_gsi(
                    run_id, status, limit - len(emails), last_evaluated_key, sort_order
                )
            else:
                response = email_repo.query_emails_by_run_id_and_created_at_gsi(
                    run_id, limit - len(emails), last_evaluated_key, sort_order
                )

            emails.extend(response.get("Items", []))
            last_evaluated_key = response.get("LastEvaluatedKey")

            if last_evaluated_key is None or len(emails) >= limit:
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
            user_id,
            "email-run_id-status-gsi" if status else "email-run_id-created_at-gsi",
        )
    )
    last_evaluated_keys = pagination_state.get("last_evaluated_keys", [])

    # Append the next_last_evaluated_key only if it is not already in the list
    if next_last_evaluated_key and next_last_evaluated_key not in last_evaluated_keys:
        last_evaluated_keys.append(next_last_evaluated_key)

    pagination_state_repo.save_pagination_state(
        {
            "user_id": user_id,
            "index_name": (
                "email-run_id-status-gsi" if status else "email-run_id-created_at-gsi"
            ),
            "last_evaluated_keys": last_evaluated_keys,
            "created_at": pagination_state.get("created_at", get_current_utc_time()),
            "updated_at": get_current_utc_time(),
            "limit": limit,
        }
    )

    # Sort the results by created_at
    emails.sort(
        key=lambda x: x.get("created_at", ""), reverse=(sort_order.upper() == "DESC")
    )

    # Encode last_evaluated_key to base64 if it's not null
    for email in emails:
        for key, value in email.items():
            if isinstance(value, Decimal):
                email[key] = float(value)

    # Find the index of the current_last_evaluated_key in last_evaluated_keys
    if current_last_evaluated_key in last_evaluated_keys:
        current_index = last_evaluated_keys.index(current_last_evaluated_key)
        previous_last_evaluated_key = (
            last_evaluated_keys[current_index - 1] if current_index > 0 else None
        )
    else:
        previous_last_evaluated_key = None

    result = {
        "data": emails[:limit],
        "previous_last_evaluated_key": previous_last_evaluated_key,
        "current_last_evaluated_key": current_last_evaluated_key,
        "next_last_evaluated_key": next_last_evaluated_key,
    }

    logger.info("Returning response with %d emails", len(emails))
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(result, cls=DecimalEncoder),
    }
