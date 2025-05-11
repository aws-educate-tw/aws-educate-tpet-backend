import json
import logging

from botocore.exceptions import ClientError
from run_repository import RunRepository

# current_user_util might be needed if we enforce run access by sender_id
# from current_user_util import CurrentUserUtil

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# No DecimalEncoder needed as RunRepository's parse_field should handle it.
# No extract_query_params needed for get_run by ID.


def lambda_handler(event: dict[str, any], context: object) -> dict[str, any]:
    """Lambda function handler for retrieving a single run by its ID."""

    aws_request_id = getattr(context, "aws_request_id", None)
    logger.info("Received event: %s", event)

    if event.get("action") == "PREWARM":
        logger.info(
            "Received a prewarm request. Skipping business logic. Request ID: %s",
            aws_request_id,
        )
        return {"statusCode": 200, "body": "Successfully warmed up"}

    try:
        run_id = event.get("pathParameters", {}).get("run_id")
        if not run_id:
            logger.error(
                "Missing run_id in pathParameters. Request ID: %s", aws_request_id
            )
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing run_id in path parameters"}),
            }
        logger.info(
            "Attempting to retrieve run with run_id: %s. Request ID: %s",
            run_id,
            aws_request_id,
        )
    except Exception as e:
        logger.error(
            "Error accessing pathParameters: %s. Request ID: %s", e, aws_request_id
        )
        return {
            "statusCode": 400,
            "body": json.dumps(
                {"message": "Invalid request format, error accessing path parameters."}
            ),
        }

    # Authentication (optional, based on requirements, e.g., if user can only get their own runs)
    # authorization_header = event["headers"].get("authorization")
    # if not authorization_header or not authorization_header.startswith("Bearer "):
    #     logger.warning("Missing or invalid Authorization header. Request ID: %s", aws_request_id)
    #     return {
    #         "statusCode": 401,
    #         "body": json.dumps({"message": "Missing or invalid Authorization header"}),
    #     }
    # access_token = authorization_header.split(" ")[1]
    # try:
    #     user_id = CurrentUserUtil().get_user_id_from_access_token(access_token)
    # except Exception as e:
    #     logger.error("Failed to get user_id from access token: %s. Request ID: %s", e, aws_request_id)
    #     return {
    #         "statusCode": 401,
    #         "body": json.dumps({"message": "Invalid or expired access token"}),
    #     }

    run_repo = RunRepository()

    try:
        run_item = run_repo.get_run_by_id(run_id)

        if not run_item:
            logger.warning(
                "Run with run_id: %s not found. Request ID: %s", run_id, aws_request_id
            )
            return {
                "statusCode": 404,
                "body": json.dumps({"message": f"Run with ID '{run_id}' not found"}),
            }

        # Calculate failed_email_count
        expected_count = run_item.get("expected_email_send_count", 0)
        success_count = run_item.get("success_email_count", 0)
        # Ensure counts are integers
        expected_count = int(expected_count) if expected_count is not None else 0
        success_count = int(success_count) if success_count is not None else 0

        run_item = {**run_item, "failed_email_count": expected_count - success_count}

        # Ensure all timestamps within nested objects are also ISO8601.
        # The `parse_field` in RunRepository should handle top-level `created_at`.
        # For nested objects like `template_file`, `spreadsheet_file`, `attachment_files`,
        # if they contain `created_at` or `updated_at` fields, these should have been
        # stored as ISO8601 strings in the JSONB, or `parse_field` needs to be enhanced
        # to recursively format them. Assuming they are stored correctly for now.

        logger.info(
            "Successfully retrieved run: %s. Request ID: %s", run_id, aws_request_id
        )
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                run_item
            ),  # parse_field in repo should ensure ISO8601 for created_at
        }

    except ClientError as e:
        logger.error(
            "Database client error while getting run %s: %s. Request ID: %s",
            run_id,
            e,
            aws_request_id,
        )
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"message": f"Database error: {e}. Request ID: {aws_request_id}"}
            ),
        }
    except Exception as e:
        logger.error(
            "Unexpected error while getting run %s: %s. Request ID: %s",
            run_id,
            e,
            aws_request_id,
        )
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "message": f"An unexpected error occurred: {e}. Request ID: {aws_request_id}"
                }
            ),
        }
