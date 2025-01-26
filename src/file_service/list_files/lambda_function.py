import base64
import json
import logging
from decimal import Decimal

from botocore.exceptions import ClientError
from current_user_util import CurrentUserUtil
from file_repository import FileRepository
from file_service_pagination_state_repository import (
    FileServicePaginationStateRepository,
)
from time_util import get_current_utc_time, get_previous_year

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects."""

    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def decode_key(encoded_key: str) -> dict[str, str]:
    """Decode a base64 encoded key into a dictionary."""
    try:
        decoded_key = json.loads(base64.b64decode(encoded_key).decode("utf-8"))
        return decoded_key
    except (json.JSONDecodeError, base64.binascii.Error) as e:
        logger.error("Invalid key format: %s", e)
        raise ValueError(
            "Invalid key format. It must be a valid base64 encoded JSON string."
        ) from e


def encode_key(decoded_key: dict[str, str]) -> str:
    """Encode a dictionary into a base64 encoded string."""
    encoded_key = base64.b64encode(json.dumps(decoded_key).encode("utf-8")).decode(
        "utf-8"
    )
    return encoded_key


def extract_query_params(event: dict[str, any]) -> dict[str, any]:
    """Extract query parameters from the API Gateway event."""
    limit: int = 10
    last_evaluated_key: str | None = None
    file_extension: str | None = None
    sort_order: str = "DESC"
    created_year: str | None = None

    # Extract query parameters if they exist
    if event.get("queryStringParameters"):
        try:
            limit = int(event["queryStringParameters"].get("limit", 10))
            last_evaluated_key = event["queryStringParameters"].get(
                "last_evaluated_key", None
            )
            sort_order = event["queryStringParameters"].get("sort_order", "DESC")
            file_extension = event["queryStringParameters"].get("file_extension", None)
            created_year = event["queryStringParameters"].get("created_year", None)
        except ValueError as e:
            logger.error("Invalid query parameter: %s", e)
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Invalid query parameter: " + str(e)}),
            }

    # Check if both file_extension and created_year are provided
    if file_extension and created_year:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {"message": "file_extension and created_year cannot be used together"}
            ),
        }

    # Log the extracted parameters
    logger.info(
        "Extracted parameters - limit: %d, last_evaluated_key: %s, sort_order: %s, file_extension: %s, created_year: %s",
        limit,
        last_evaluated_key,
        sort_order,
        file_extension,
        created_year,
    )

    return {
        "limit": limit,
        "last_evaluated_key": last_evaluated_key,
        "file_extension": file_extension,
        "sort_order": sort_order,
        "created_year": created_year,
    }


def lambda_handler(event: dict[str, any], context: object) -> dict[str, any]:
    """Lambda function handler for listing files."""

    # Identify if the incoming event is a prewarm request
    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    extracted_params = extract_query_params(event)
    if isinstance(extracted_params, dict) and extracted_params.get("statusCode"):
        return extracted_params

    limit: int = extracted_params["limit"]
    last_evaluated_key: str | None = extracted_params["last_evaluated_key"]
    file_extension: str | None = extracted_params["file_extension"]
    sort_order: str = extracted_params["sort_order"]
    created_year: str | None = extracted_params["created_year"]

    # Determine the correct index_name based on the query parameters
    if file_extension:
        index_name = "file_extension-created_at-gsi"
    else:
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
    file_repo = FileRepository()
    pagination_state_repo = FileServicePaginationStateRepository()

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
                "headers": {"Content-Type": "application/json"},
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

    files = []

    # Query the table using the provided parameters
    try:
        if file_extension:
            response = file_repo.query_files_by_file_extension_and_created_at_gsi(
                file_extension, limit, last_evaluated_key, sort_order
            )
            files.extend(response.get("Items", []))
        else:
            for year in years_to_query:
                while True:
                    response = file_repo.query_files_by_created_year_and_created_at_gsi(
                        year, limit - len(files), last_evaluated_key, sort_order
                    )
                    files.extend(response.get("Items", []))
                    last_evaluated_key = response.get("LastEvaluatedKey")

                    if last_evaluated_key is None or len(files) >= limit:
                        break

                if len(files) >= limit:
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
    files.sort(key=lambda x: x.get("created_at", ""), reverse=reverse_order)

    # Encode last_evaluated_key to base64 if it's not null
    for file in files:
        for key, value in file.items():
            if isinstance(value, Decimal):
                file[key] = float(value)

    # Find the index of the current_last_evaluated_key in last_evaluated_keys
    if current_last_evaluated_key in last_evaluated_keys:
        current_index = last_evaluated_keys.index(current_last_evaluated_key)
        previous_last_evaluated_key = (
            last_evaluated_keys[current_index - 1] if current_index > 0 else None
        )
    else:
        previous_last_evaluated_key = None

    result = {
        "data": files[:limit],
        "previous_last_evaluated_key": previous_last_evaluated_key,
        "current_last_evaluated_key": current_last_evaluated_key,
        "next_last_evaluated_key": next_last_evaluated_key,
    }

    logger.info("Returning response with %d files", len(files))
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(result, cls=DecimalEncoder),
    }
