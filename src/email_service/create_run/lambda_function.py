import json
import logging
import uuid

from botocore.exceptions import ClientError
from recipient_source_enum import RecipientSource
from run_repository import RunRepository
from run_type_enum import RunType

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

run_repo = RunRepository()


def lambda_handler(event: dict[str, any], context: object) -> dict[str, any]:
    """Lambda function handler for creating an empty run with a specified run_type."""

    valid_run_types = [rt.value for rt in RunType]
    valid_recipient_sources = [rs.value for rs in RecipientSource]

    aws_request_id = getattr(context, "aws_request_id", None)
    logger.info("Received event: %s", event)

    if event.get("action") == "PREWARM":
        logger.info(
            "Received a prewarm request. Skipping business logic. Request ID: %s",
            aws_request_id,
        )
        return {"statusCode": 200, "body": "Successfully warmed up"}

    try:
        body = json.loads(event.get("body", "{}"))
        run_type = body.get("run_type")
        recipient_source = body.get("recipient_source", "DIRECT")

        # Validate required fields
        if not run_type:
            logger.error(
                "Missing required field 'run_type'. Request ID: %s", aws_request_id
            )
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "message": f"'run_type' is required and cannot be empty. the valid values include {', '.join(valid_run_types)}",
                        "error": "Missing required field",
                        "request_id": aws_request_id,
                    }
                ),
            }

        if run_type not in valid_run_types:
            logger.error(
                "Invalid value for run_type: %s. Request ID: %s",
                run_type,
                aws_request_id,
            )
            return {
                "statusCode": 422,
                "body": json.dumps(
                    {
                        "message": f"Invalid value for run_type. Allowed: {', '.join(valid_run_types)}",
                        "error": "Invalid value",
                        "request_id": aws_request_id,
                    }
                ),
            }

        if recipient_source and recipient_source not in valid_recipient_sources:
            logger.error(
                "Invalid value for recipient_source: %s. Request ID: %s",
                recipient_source,
                aws_request_id,
            )
            return {
                "statusCode": 422,
                "body": json.dumps(
                    {
                        "message": f"Invalid value for recipient_source. Allowed: {', '.join(valid_recipient_sources)}",
                        "error": "Invalid value",
                        "request_id": aws_request_id,
                    }
                ),
            }

        # Set default values for the new run
        run_data = {
            "run_id": str(uuid.uuid4()),
            "run_type": run_type,
            "recipient_source": recipient_source,
            "expected_email_send_count": 0,
            "success_email_count": 0,
            "failed_email_count": 0,
            "attachment_file_ids": [],
            "attachment_files": [],
            "recipients": [],
            "is_generate_certificate": False,
            "reply_to": "",
            "sender_local_part": "",
            "subject": "",
            "template_file_id": "",
            "spreadsheet_file_id": None,
            "spreadsheet_file": None,
            "template_file": None,
        }

        logger.info(
            "Creating run with data: %s. Request ID: %s", run_data, aws_request_id
        )

        try:
            # Create the run in the database using upsert_run
            run_id = run_repo.upsert_run(run_data)

            if not run_id:
                logger.error("Failed to create run. Request ID: %s", aws_request_id)
                return {
                    "statusCode": 500,
                    "body": json.dumps(
                        {
                            "message": "Failed to create run",
                            "error": "Database error",
                            "request_id": aws_request_id,
                        }
                    ),
                }

            # Get the created run to return it
            created_run = run_repo.get_run_by_id(run_id)

            logger.info(
                "Successfully created run with ID: %s. Request ID: %s",
                run_id,
                aws_request_id,
            )

            return {
                "statusCode": 201,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(created_run),
            }

        except ClientError as e:
            logger.error(
                "Database client error while creating run: %s. Request ID: %s",
                e,
                aws_request_id,
            )
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "message": f"Database error: {e}",
                        "error": "Database error",
                        "request_id": aws_request_id,
                    }
                ),
            }

    except json.JSONDecodeError as e:
        logger.error(
            "Invalid JSON in request body: %s. Request ID: %s", e, aws_request_id
        )
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "message": "Invalid JSON in request body",
                    "error": "Invalid request format",
                    "request_id": aws_request_id,
                }
            ),
        }
    except Exception as e:
        logger.error("Unexpected error: %s. Request ID: %s", e, aws_request_id)
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "message": f"An unexpected error occurred: {e}",
                    "error": "Server error",
                    "request_id": aws_request_id,
                }
            ),
        }
