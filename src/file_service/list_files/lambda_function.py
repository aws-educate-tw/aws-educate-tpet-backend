import base64
import json
import logging
from decimal import Decimal
from typing import Optional

from botocore.exceptions import ClientError
from file_repository import FileRepository
from file_service_pagination_state_repository import (
    FileServicePaginationStateRepository,
)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects."""

    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


def decode_key(encoded_key: str) -> dict:
    """Decode a base64 encoded key into a dictionary."""
    try:
        decoded_key = json.loads(base64.b64decode(encoded_key).decode("utf-8"))
        return decoded_key
    except (json.JSONDecodeError, base64.binascii.Error) as e:
        logger.error("Invalid key format: %s", e)
        raise ValueError(
            "Invalid key format. It must be a valid base64 encoded JSON string."
        ) from e


def encode_key(decoded_key: dict) -> str:
    """Encode a dictionary into a base64 encoded string."""
    encoded_key = base64.b64encode(json.dumps(decoded_key).encode("utf-8")).decode(
        "utf-8"
    )
    return encoded_key


def extract_query_params(event: dict) -> dict:
    """Extract query parameters from the API Gateway event."""
    limit: int = 10
    last_evaluated_key: Optional[str] = None
    file_extension: Optional[str] = None
    sort_order: str = "DESC"

    # Extract query parameters if they exist
    if event.get("queryStringParameters"):
        try:
            limit = int(event["queryStringParameters"].get("limit", 10))
            last_evaluated_key = event["queryStringParameters"].get(
                "last_evaluated_key", None
            )
            sort_order = event["queryStringParameters"].get("sort_order", "DESC")
            file_extension = event["queryStringParameters"].get("file_extension", None)
        except ValueError as e:
            logger.error("Invalid query parameter: %s", e)
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Invalid query parameter: " + str(e)}),
            }

    if not file_extension:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {"message": "file_extension is a required query parameter"}
            ),
        }

    # Log the extracted parameters
    logger.info(
        "Extracted parameters - limit: %d, last_evaluated_key: %s, sort_order: %s, file_extension: %s",
        limit,
        last_evaluated_key,
        sort_order,
        file_extension,
    )

    return {
        "limit": limit,
        "last_evaluated_key": last_evaluated_key,
        "file_extension": file_extension,
        "sort_order": sort_order,
    }


def lambda_handler(event: dict, context: object) -> dict:
    """Lambda function handler for listing files."""
    extracted_params = extract_query_params(event)
    if isinstance(extracted_params, dict) and extracted_params.get("statusCode"):
        return extracted_params

    limit: int = extracted_params["limit"]
    last_evaluated_key: Optional[str] = extracted_params["last_evaluated_key"]
    file_extension: str = extracted_params["file_extension"]
    sort_order: str = extracted_params["sort_order"]
    user_id: str = "dummy_uploader_id"

    # Init dynamoDB entities
    file_repo = FileRepository()
    pagination_state_repo = FileServicePaginationStateRepository()

    if last_evaluated_key:
        try:
            # Decode the base64 last_evaluated_key
            current_last_evaluated_key = last_evaluated_key
            last_evaluated_key = decode_key(last_evaluated_key)
            logger.info("Decoded last_evaluated_key: %s", last_evaluated_key)

            # Get the previous last evaluated key from the state
            state = pagination_state_repo.get_pagination_state_by_user_id(user_id)
            previous_last_evaluated_key = state.get("previous_last_evaluated_key")
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
        previous_last_evaluated_key = None

    # Query the table using the provided parameters

    try:
        response = file_repo.query_files(
            file_extension, limit, last_evaluated_key, sort_order
        )
        logger.info("Query successful")
    except ClientError as e:
        logger.error("Query failed: %s", e)
        return {"statusCode": 400, "body": json.dumps({"message": str(e)})}

    files: list[dict] = response.get("Items", [])
    next_last_evaluated_key: Optional[str] = response.get("LastEvaluatedKey")

    # Encode last_evaluated_key to base64 if it's not null
    if next_last_evaluated_key:
        next_last_evaluated_key = encode_key(next_last_evaluated_key)

    # Store the pagination state for the next request
    pagination_state_repo.save_pagination_state(
        {
            "user_id": user_id,
            "previous_last_evaluated_key": current_last_evaluated_key,
            "current_last_evaluated_key": next_last_evaluated_key,
            "next_last_evaluated_key": next_last_evaluated_key,
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

    result = {
        "data": files,
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
