import json
import boto3
import uuid
from datetime import datetime, timedelta
import logging

logger = logging.getLogger()
logger.setLevel("INFO")

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("campaign")

def lambda_handler(event, context):
    try:
        body = json.loads(event["body"])

        campaign_id = uuid.uuid4().hex
        campaign_name = body["campaign_name"]
        description = body["description"]
        start_date = body["start_date"]
        end_date = body["end_date"]
        participant_limit = body["participant_limit"]
        locations = body["locations"]

        # Determine the status based on the current date and time
        current_time = datetime.now()
        start_time = datetime.fromisoformat(start_date[:-1])
        end_time = datetime.fromisoformat(end_date[:-1])

        if current_time < start_time:
            status = "UPCOMING"
        elif start_time <= current_time <= end_time:
            status = "ACTIVE"
        else:
            status = "COMPLETED"

        created_at = (datetime.now() + timedelta(hours=8)).strftime(TIME_FORMAT + "Z")
        updated_at = (datetime.now() + timedelta(hours=8)).strftime(TIME_FORMAT + "Z")

        item = {
            "campaign_id": campaign_id,
            "start_date": start_date,
            "end_date": end_date,
            "participant_limit": participant_limit,
            "campaign_name": campaign_name,
            "description": description,
            "locations": json.dumps(locations),
            "created_at": created_at,
            "updated_at": updated_at,
            "status": status,
        }

        table.put_item(Item=item)
        logger.info("Campaign created successfully with ID: %s", campaign_id)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "Campaign created successfully", 
                 "campaign_id": campaign_id,
                 "campaign_name": campaign_name,
                 "description": description,
                 "start_date": start_date,
                 "end_date": end_date,
                 "participant_limit": participant_limit,
                 "locations": locations,
                 "created_at": created_at,
                 "updated_at": updated_at,
                 "status": status}
            ),
        }
    except json.JSONDecodeError:
        error_message = "Invalid JSON format in request body"
        logger.error("JSONDecodeError: %s", error_message)
        return {"statusCode": 400, "body": json.dumps({"message": error_message})}
    except KeyError as e:
        error_message = "Missing required field: %s" % str(e)
        logger.error("KeyError: %s", error_message)
        return {"statusCode": 400, "body": json.dumps({"message": error_message})}
    except Exception as e:
        error_message = str(e)
        logger.error("Exception: %s", error_message, exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"message": error_message})}
