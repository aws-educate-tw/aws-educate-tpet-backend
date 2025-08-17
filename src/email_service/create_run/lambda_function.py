import json
import logging
import uuid

from botocore.exceptions import ClientError
from run_repository import RunRepository

# current_user_util might be needed if we enforce run access by sender_id
# from current_user_util import CurrentUserUtil

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Valid values for run_type and recipient_source
VALID_RUN_TYPES = ["WEBHOOK", "EMAIL"]
VALID_RECIPIENT_SOURCES = ["DIRECT", "SPREADSHEET"]

run_repo = RunRepository()

def lambda_handler(event: dict[str, any], context: object) -> dict[str, any]:
    """Lambda function handler for creating an empty run with a specified run_type."""
    
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
                "body": json.dumps({
                    "message": "'run_type' is required and cannot be empty. the valid values include 'WEBHOOK', 'EMAIL'",
                    "error": "Missing required field",
                    "request_id": aws_request_id
                }),
            }
            
        # Validate run_type value
        if run_type not in VALID_RUN_TYPES:
            logger.error(
                "Invalid value for run_type: %s. Request ID: %s", 
                run_type, 
                aws_request_id
            )
            return {
                "statusCode": 422,
                "body": json.dumps({
                    "message": "Invalid value for run_type. Allowed: WEBHOOK, EMAIL",
                    "error": "Invalid value",
                    "request_id": aws_request_id
                }),
            }
            
        # Validate recipient_source if provided
        if recipient_source and recipient_source not in VALID_RECIPIENT_SOURCES:
            logger.error(
                "Invalid value for recipient_source: %s. Request ID: %s", 
                recipient_source, 
                aws_request_id
            )
            return {
                "statusCode": 422,
                "body": json.dumps({
                    "message": "Invalid value for recipient_source. Allowed: DIRECT, SPREADSHEET",
                    "error": "Invalid value",
                    "request_id": aws_request_id
                }),
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
            "template_file": None
        }
        
        # Add sender information if available
        # Uncomment and use this when authentication is implemented
        # if authorization_header:
        #     user_id = "9881b370-0031-7037-b42e-ef737d3aa382"  # Example, replace with actual user ID from token
        #     run_data["sender_id"] = user_id
        #     run_data["sender"] = {
        #         "email": "surveycake@aws-educate.tw",
        #         "user_id": user_id,
        #         "username": "surveycake",
        #         "cognito_sub": user_id
        #     }
        
        # For now, hardcode sender info for demonstration/testing
        run_data["sender_id"] = "9881b370-0031-7037-b42e-ef737d3aa382"
        run_data["sender"] = {
            "email": "surveycake@aws-educate.tw",
            "user_id": "9881b370-0031-7037-b42e-ef737d3aa382",
            "username": "surveycake",
            "cognito_sub": "9881b370-0031-7037-b42e-ef737d3aa382"
        }
        
        logger.info("Creating run with data: %s. Request ID: %s", run_data, aws_request_id)
        
        try:
            # Create the run in the database using upsert_run
            run_id = run_repo.upsert_run(run_data)
            
            if not run_id:
                logger.error(
                    "Failed to create run. Request ID: %s", aws_request_id
                )
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "message": "Failed to create run",
                        "error": "Database error",
                        "request_id": aws_request_id
                    }),
                }
                
            # Get the created run to return it
            created_run = run_repo.get_run_by_id(run_id)
            
            logger.info(
                "Successfully created run with ID: %s. Request ID: %s",
                run_id,
                aws_request_id,
            )
            
            # Return the newly created run with a 200 status code (as specified in requirements)
            return {
                "statusCode": 200,  # Changed from 201 to 200 as per API design
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
                "body": json.dumps({
                    "message": f"Database error: {e}",
                    "error": "Database error",
                    "request_id": aws_request_id
                }),
            }
            
    except json.JSONDecodeError as e:
        logger.error(
            "Invalid JSON in request body: %s. Request ID: %s", e, aws_request_id
        )
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": "Invalid JSON in request body",
                "error": "Invalid request format",
                "request_id": aws_request_id
            }),
        }
    except Exception as e:
        logger.error(
            "Unexpected error: %s. Request ID: %s", e, aws_request_id
        )
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": f"An unexpected error occurred: {e}",
                "error": "Server error",
                "request_id": aws_request_id
            }),
        }