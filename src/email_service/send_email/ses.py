import logging
import re

import time_util
from dynamodb import save_to_dynamodb

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def send_email(ses_client, email_title, template_content, row, display_name):
    try:
        template_content = template_content.replace("\r", "")
        template_content = re.sub(r"\{\{(.*?)\}\}", r"{\1}", template_content)
        recipient_email = row.get("Email")
        if not recipient_email:
            logger.warning("Email address not found in row: %s", row)
            return None, "FAILED"
        try:
            formatted_row = {k: str(v) for k, v in row.items()}
            formatted_content = template_content.format(**formatted_row)
            source_email = "awseducate.cloudambassador@gmail.com"
            formatted_source_email = f"{display_name} <{source_email}>"
            ses_client.send_email(
                Source=formatted_source_email,
                Destination={"ToAddresses": [recipient_email]},
                Message={
                    "Subject": {"Data": email_title},
                    "Body": {"Html": {"Data": formatted_content}},
                },
            )
            sent_time = time_util.get_current_utc_time()
            logger.info(
                "Email sent to %s at %s",
                row.get("Email", "Unknown"),
                sent_time,
            )
            return sent_time, "SUCCESS"
        except Exception as e:
            logger.error("Failed to send email to %s: %s", recipient_email, e)
            return None, "FAILED"
    except Exception as e:
        logger.error("Error in send_email: %s", e)
        return None, "FAILED"


def process_email(
    ses_client,
    email_title,
    template_content,
    row,
    display_name,
    run_id,
    template_file_id,
    spreadsheet_id,
    email_id,
):
    recipient_email = str(row.get("Email", ""))
    if not re.match(r"[^@]+@[^@]+\.[^@]+", recipient_email):
        logger.warning("Invalid email address provided: %s", recipient_email)
        return "FAILED", email_id

    sent_time, status = send_email(
        ses_client, email_title, template_content, row, display_name
    )
    updated_at = time_util.get_current_utc_time()
    save_to_dynamodb(
        run_id,
        email_id,
        display_name,
        status,
        recipient_email,
        template_file_id,
        spreadsheet_id,
        time_util.get_current_utc_time(),
        sent_at=sent_time,
        updated_at=updated_at,
    )
    return status, email_id
