import io
import logging
import os
import uuid

import boto3
import pandas as pd
import time_util
from current_user_util import current_user_util
from data_util import convert_float_to_decimal
from email_repository import EmailRepository
from jwt_util import generate_rsvp_token
from run_type_enum import RunType
from s3 import read_sheet_data_from_s3
from sqs import delete_sqs_message, get_sqs_message, send_message_to_queue
from template_variable_db_column_mapping_util import map_recipient_name

from file_service import FileService
from rsvp_service import RSVPService

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get environment variables
CREATE_EMAIL_SQS_QUEUE_URL = os.getenv(
    "CREATE_EMAIL_SQS_QUEUE_URL"
)  # Queue for receiving create email requests
SEND_EMAIL_SQS_QUEUE_URL = os.getenv(
    "SEND_EMAIL_SQS_QUEUE_URL"
)  # Queue for triggering email sending

DEFAULT_RUN_TYPE = "EMAIL"

# Initialize services
file_service = FileService()
email_repository = EmailRepository()
rsvp_service = RSVPService()


def prepare_email_item(run_id: str, email_data: dict, row_data: dict) -> dict:
    """
    Prepare an email item with the necessary data.

    :param run_id: The run ID for tracking the email operation
    :param email_data: Dictionary containing email metadata (including template_variables)
    :param row_data: Dictionary containing recipient data and template variables
    :return: Created email item dictionary
    """
    # Reuse RSVP-generated email_id when present to keep token linkage consistent.
    email_id = row_data.get("email_id") or str(uuid.uuid4().hex)
    row_data = convert_float_to_decimal(row_data)
    created_at = time_util.get_current_utc_time()

    # Map template variables to recipient_name column
    template_variables = email_data.get("template_variables", [])
    recipient_name = map_recipient_name(template_variables, row_data)

    return {
        "run_id": run_id,
        "email_id": email_id,
        "subject": email_data["subject"],
        "display_name": email_data["display_name"],
        "template_file_id": email_data["template_file_id"],
        "spreadsheet_file_id": email_data.get("spreadsheet_file_id"),
        "attachment_file_ids": email_data.get("attachment_file_ids", []),
        "status": "PENDING",
        "recipient_email": row_data.get("Email"),
        "recipient_name": recipient_name,
        "row_data": row_data,
        "created_at": created_at,
        "is_generate_certificate": email_data.get("is_generate_certificate", False),
        "sender_id": email_data["sender_id"],
        "sender_username": current_user_util.get_current_user_info().get("username"),
        "reply_to": email_data.get("reply_to"),
        "sender_local_part": email_data.get("sender_local_part"),
        "cc": email_data.get("cc"),
        "bcc": email_data.get("bcc"),
    }


def enqueue_email_to_send_email_sqs_queue(email_item: dict) -> None:
    """
    Send email item to the send email queue.

    :param email_item: The email item to be sent
    """
    message = {
        "run_id": email_item["run_id"],
        "email_id": email_item["email_id"],
        "recipient_email": email_item["recipient_email"],
        "subject": email_item["subject"],
        "template_file_id": email_item["template_file_id"],
        "display_name": email_item["display_name"],
        "row_data": email_item["row_data"],
        "attachment_file_ids": email_item["attachment_file_ids"],
        "is_generate_certificate": email_item["is_generate_certificate"],
        "sender_id": email_item["sender_id"],
        "reply_to": email_item.get("reply_to"),
        "sender_local_part": email_item.get("sender_local_part"),
        "cc": email_item.get("cc"),
        "bcc": email_item.get("bcc"),
        "access_token": current_user_util.get_current_user_access_token(),
    }

    try:
        send_message_to_queue(SEND_EMAIL_SQS_QUEUE_URL, message)
    except Exception as e:
        logger.error(
            "Failed to queue email %s for sending: %s", email_item["email_id"], str(e)
        )
        # Update email status to FAILED if we couldn't queue it
        email_repository.update_email_status(
            run_id=email_item["run_id"],
            email_id=email_item["email_id"],
            status="FAILED",
        )
        raise


def build_recipient_list_from_sqs_message(sqs_message: dict) -> list[dict]:
    """
    Process recipients based on the source type (SPREADSHEET or DIRECT).

    :param sqs_message: The SQS message containing recipient information
    :return: List of recipient data dictionaries
    """
    recipient_source = sqs_message.get("recipient_source", "SPREADSHEET")

    if recipient_source == "SPREADSHEET":
        spreadsheet_info = file_service.get_file_info(
            sqs_message["spreadsheet_file_id"],
            current_user_util.get_current_user_access_token(),
        )
        spreadsheet_s3_object_key = spreadsheet_info["s3_object_key"]
        sheet_data, _ = read_sheet_data_from_s3(spreadsheet_s3_object_key)
        logger.info("Read sheet data from S3: %s", sheet_data)
        return sheet_data
    else:  # DIRECT mode
        sheet_data = []
        for recipient in sqs_message["recipients"]:
            recipient_data = {
                "Email": recipient["email"],
                **recipient["template_variables"],
            }
            sheet_data.append(recipient_data)
        logger.info("Processed direct recipients data: %s", sheet_data)
        return sheet_data


def upsert_emails_and_enqueue_emails_to_send_email_sqs_queue(
    sqs_message: dict,
) -> None:
    """
    Processes recipients from the SQS message and creates corresponding email items.

    :param sqs_message: The SQS message containing run and recipient data.
    """
    recipients_data = build_recipient_list_from_sqs_message(sqs_message)

    for row_data in recipients_data:
        # Create and save email item
        email_item = prepare_email_item(sqs_message["run_id"], sqs_message, row_data)
        email_repository.upsert_email(email_item)

        # Enqueue the email for sending
        enqueue_email_to_send_email_sqs_queue(email_item)

    logger.info(
        "Successfully processed all recipients for run_id: %s",
        sqs_message["run_id"],
    )


def process_rsvp_emails_and_update_spreadsheet(sqs_message: dict) -> list[dict]:
    """
    Process RSVP emails: import participants to RSVP service, generate tokens,
    and update spreadsheet with participant_id, email_id, and token.

    :param sqs_message: The SQS message containing run and recipient data.
    :return: Updated recipient rows for downstream email upsert/enqueue.
    """
    run_id = sqs_message["run_id"]
    campaign_id = sqs_message.get("campaign_id")
    spreadsheet_file_id = sqs_message.get("spreadsheet_file_id")
    registration_deadline = sqs_message.get("registration_deadline")

    if not registration_deadline:
        logger.error("registration_deadline is missing for RSVP run_type")
        raise ValueError("registration_deadline is required for RSVP run_type")

    # Read spreadsheet data
    spreadsheet_info = file_service.get_file_info(
        spreadsheet_file_id,
        current_user_util.get_current_user_access_token(),
    )
    spreadsheet_s3_object_key = spreadsheet_info["s3_object_key"]
    sheet_data, columns = read_sheet_data_from_s3(spreadsheet_s3_object_key)

    logger.info(
        "Processing RSVP emails for run_id: %s, campaign_id: %s", run_id, campaign_id
    )

    # Process each row
    updated_sheet_data = []
    for row_data in sheet_data:
        email = row_data.get("Email")
        name = row_data.get(
            "Name", row_data.get("姓名", email)
        )  # Fallback to email if no name

        email_id = str(uuid.uuid4().hex)

        # Import participant to RSVP service
        try:
            response = rsvp_service.import_participant(
                run_id=run_id,
                email=email,
                campaign_id=campaign_id,
                name=name,
            )

            if response.get("status") != "SUCCESS":
                logger.error(
                    "Failed to import participant to RSVP service: %s", response
                )
                raise ValueError("Failed to import participant to RSVP service")

            participant_id = (response.get("data") or {}).get("participant_id")
            if not participant_id:
                logger.error(
                    "RSVP service import_participant returned no participant_id: %s",
                    response,
                )
                raise ValueError(
                    "RSVP service import_participant returned no participant_id"
                )

            logger.info(
                "Imported participant: email=%s, participant_id=%s, email_id=%s",
                email,
                participant_id,
                email_id,
            )
        except Exception as e:
            logger.error("Failed to import participant %s: %s", email, e)
            raise

        # Generate JWT token
        try:
            token = generate_rsvp_token(
                run_id=run_id,
                participant_id=participant_id,
                email_id=email_id,
                campaign_id=campaign_id,
                name=name,
                expiration_datetime=registration_deadline,
            )
            logger.info("Generated JWT token for participant_id: %s", participant_id)
        except Exception as e:
            logger.error(
                "Failed to generate JWT token for participant %s: %s", participant_id, e
            )
            raise

        # Update row with participant_id, email_id, and token
        updated_row = {
            **row_data,
            "participant_id": participant_id,
            "email_id": email_id,
            "jwt_token": token,
        }
        updated_sheet_data.append(updated_row)

    # Write updated data back to spreadsheet
    try:
        # Create DataFrame from updated data
        df = pd.DataFrame(updated_sheet_data)

        # Reorder columns: original columns first, then new columns
        existing_cols = [col for col in columns if col in df.columns]
        new_cols = [col for col in df.columns if col not in columns]
        df = df[existing_cols + new_cols]

        # Write to Excel in memory
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1")

        # Upload to S3
        excel_buffer.seek(0)
        s3 = boto3.client("s3")
        bucket_name = os.getenv("BUCKET_NAME")
        s3.put_object(
            Bucket=bucket_name,
            Key=spreadsheet_s3_object_key,
            Body=excel_buffer.getvalue(),
        )

        logger.info(
            "Successfully updated spreadsheet with participant_id, email_id, and tokens for run_id: %s",
            run_id,
        )
    except Exception as e:
        logger.error("Failed to write updated spreadsheet data to S3: %s", e)
        raise

    logger.info(
        "Successfully processed all RSVP participants for run_id: %s",
        run_id,
    )
    return updated_sheet_data


def lambda_handler(event, context):
    """
    AWS Lambda handler function to process email creation requests.

    :param event: The event data from SQS
    :param context: The runtime information of the Lambda function
    """
    logger.info("Lambda triggered with event: %s", event)

    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    for record in event["Records"]:
        sqs_message = None
        try:
            sqs_message = get_sqs_message(record)
            access_token = sqs_message["access_token"]
            run_type = sqs_message.get("run_type", DEFAULT_RUN_TYPE)

            # Set the current user information
            current_user_util.set_current_user_by_access_token(access_token)

            if run_type == RunType.WEBHOOK.value:
                # For WEBHOOK, append emails without checking for existence.
                # The SQS message from validate_input contains only the new recipients.
                logger.info(
                    "Processing WEBHOOK run_type for run_id: %s", sqs_message["run_id"]
                )
                upsert_emails_and_enqueue_emails_to_send_email_sqs_queue(sqs_message)
            else:
                # For other run_types (like RSVP), maintain idempotency check
                # to prevent reprocessing the entire spreadsheet.
                existing_emails = email_repository.list_emails(
                    {
                        "run_id": sqs_message["run_id"],
                        "limit": 1,
                    }
                )

                if not existing_emails:
                    if run_type == RunType.RSVP.value:
                        process_rsvp_emails_and_update_spreadsheet(sqs_message)

                    upsert_emails_and_enqueue_emails_to_send_email_sqs_queue(
                        sqs_message,
                    )
                else:
                    logger.info(
                        "Emails already exist for run_id: %s. Skipping creation.",
                        sqs_message["run_id"],
                    )

        except Exception as e:
            logger.error("Error processing message: %s", e)
            raise
        finally:
            if sqs_message and CREATE_EMAIL_SQS_QUEUE_URL:
                try:
                    delete_sqs_message(
                        CREATE_EMAIL_SQS_QUEUE_URL,
                        sqs_message["receipt_handle"],
                    )
                    logger.info(
                        "Deleted message from SQS: %s", sqs_message["receipt_handle"]
                    )
                except Exception as e:
                    logger.error("Error deleting SQS message: %s", e)
            elif not CREATE_EMAIL_SQS_QUEUE_URL:
                logger.error(
                    "CREATE_EMAIL_SQS_QUEUE_URL is not available: %s",
                    CREATE_EMAIL_SQS_QUEUE_URL,
                )
