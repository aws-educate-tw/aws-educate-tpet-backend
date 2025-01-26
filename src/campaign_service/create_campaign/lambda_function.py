import json
import logging

from dynamodb import create_campaign
from time_util import get_current_utc_time, parse_iso8601_to_datetime

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


def get_campaign_status(start_date: str, end_date: str) -> str:
    """
    Determine the event status based on the current date and time.

    :param start_date: Event start date in ISO 8601 format.
    :param end_date: Event end date in ISO 8601 format.
    :return: Event status as a string.
    """
    # Parse the start and end dates
    start_time = parse_iso8601_to_datetime(start_date)
    end_time = parse_iso8601_to_datetime(end_date)

    # Get the current time in UTC
    current_time = parse_iso8601_to_datetime(get_current_utc_time())

    # Determine the status based on the current date and time
    if current_time < start_time:
        return "UPCOMING"
    elif current_time <= end_time:
        return "ACTIVE"
    else:
        return "COMPLETED"


def lambda_handler(event, context):
    try:
        body = json.loads(event["body"])

        # Calculate the campaign status
        body["status"] = get_campaign_status(
            start_date=body["start_date"], end_date=body["end_date"]
        )

        # Create the campaign with the given body including status
        campaign_details = create_campaign(body)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Campaign created successfully",
                    **campaign_details,
                }
            ),
        }
    except json.JSONDecodeError:
        error_message = "Invalid JSON format in request body"
        logger.error("JSONDecodeError: %s", error_message)
        return {"statusCode": 400, "body": json.dumps({"message": error_message})}
    except KeyError as e:
        error_message = f"Missing required field: {str(e)}"
        logger.error("KeyError: %s", error_message)
        return {"statusCode": 400, "body": json.dumps({"message": error_message})}
    except Exception as e:
        error_message = str(e)
        logger.error("Exception: %s", error_message, exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"message": error_message})}
