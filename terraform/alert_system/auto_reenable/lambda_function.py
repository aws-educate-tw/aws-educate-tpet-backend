import json
import os
import logging
import boto3
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from alert_util import build_blocks
from incident_repository import IncidentRepository
from slack_util import post_thread_message, update_incident_message

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cw = boto3.client("cloudwatch")
incident_repo = IncidentRepository()
slack = WebClient(token=SLACK_BOT_TOKEN)

def lambda_handler(event, context):
    """
    Auto re-enable alarm actions when alarm state changes to OK.
    This ensures alarms can send notifications for future incidents.
    
    Returns:
        dict: Response with statusCode and body
            - 200: Successfully processed
            - 400: Invalid input/bad request
            - 500: Server error
    """
    try:
        logger.info("=== Incoming Event ===")
        logger.info(json.dumps(event))
        
        # Validate event structure
        if "detail" not in event:
            logger.error("Missing 'detail' in event")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid event structure: missing 'detail'"})
            }
        
        detail = event.get("detail", {})
        alarm_name = detail.get("alarmName")
        state_value = detail.get("state", {}).get("value")
        
        # Validate required fields
        if not alarm_name:
            logger.error("Missing alarm name in event detail")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required field: alarmName"})
            }
        
        if not state_value:
            logger.error(f"Missing state value for alarm {alarm_name}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required field: state.value", "alarm": alarm_name})
            }
        
        logger.info(f"Processing alarm: {alarm_name}, State: {state_value}")
        
        # Only process when state becomes OK
        if state_value != "OK":
            logger.info(f"Alarm state is {state_value}, no action needed")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "No action needed",
                    "alarm": alarm_name,
                    "state": state_value,
                    "reason": "Only OK state triggers auto-reenable"
                })
            }
        
        # Re-enable alarm actions
        try:
            cw.enable_alarm_actions(AlarmNames=[alarm_name])
            logger.info(f"Successfully re-enabled alarm actions for {alarm_name}")
        except cw.exceptions.ResourceNotFoundException:
            logger.error(f"Alarm not found: {alarm_name}")
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Alarm not found", "alarm": alarm_name})
            }
        except Exception as e:
            logger.error(f"Failed to re-enable alarm actions for {alarm_name}: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Failed to re-enable alarm actions",
                    "alarm": alarm_name,
                    "details": str(e)
                })
            }
        
        # Get the incident from DynamoDB
        try:
            item = incident_repo.get_incident(alarm_name)
        except Exception as e:
            logger.error(f"Failed to get incident for {alarm_name}: {e}", exc_info=True)
            # Alarm was re-enabled, but we couldn't update incident status
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Failed to retrieve incident data",
                    "alarm": alarm_name,
                    "alarm_reenabled": True,
                    "details": str(e)
                })
            }
        
        # If no incident exists, we're done
        if not item:
            logger.info(f"No incident found for {alarm_name}")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Alarm re-enabled, no incident found",
                    "alarm": alarm_name,
                    "alarm_reenabled": True
                })
            }
        
        # If incident is already closed, we're done
        if not item.get("incident_open", False):
            logger.info(f"Incident already closed for {alarm_name}")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Alarm re-enabled, incident already closed",
                    "alarm": alarm_name,
                    "alarm_reenabled": True
                })
            }
        
        # Update Slack message to RESOLVED state
        description = detail.get("alarmDescription", "Alarm recovered")
        blocks, color = build_blocks(alarm_name, description, "RESOLVED")
        
        slack_updated = False
        try:
            update_incident_message(
                slack_client=slack,
                channel=item["slack_channel"],
                ts=item["slack_ts"],
                alarm_name=alarm_name,
                incident_state="RESOLVED",
                blocks=blocks,
                color=color
            )
            logger.info(f"Updated Slack message to RESOLVED for {alarm_name}")
            slack_updated = True
        except SlackApiError as e:
            logger.error(f"Slack API error updating message for {alarm_name}: {e.response['error']}", exc_info=True)
            # Continue to update DynamoDB even if Slack update fails
        except Exception as e:
            logger.error(f"Unexpected error updating Slack message for {alarm_name}: {e}", exc_info=True)
            # Continue to update DynamoDB even if Slack update fails
        
        # Update DynamoDB to mark incident as closed
        try:
            incident_repo.close_incident(alarm_name, "RESOLVED")
            logger.info(f"Closed incident in DynamoDB for {alarm_name}")
        except Exception as e:
            logger.error(f"Failed to close incident in DynamoDB for {alarm_name}: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Failed to update incident status",
                    "alarm": alarm_name,
                    "alarm_reenabled": True,
                    "slack_updated": slack_updated,
                    "details": str(e)
                })
            }
        
        # Send thread notification (non-critical)
        notification_sent = False
        try:
            message = "✅ Alarm actions have been automatically re-enabled. Future incidents will trigger notifications."
            post_thread_message(
                slack_client=slack,
                channel=item["slack_channel"],
                thread_ts=item["slack_ts"],
                message=message
            )
            logger.info(f"Sent auto-reenable notification for {alarm_name}")
            notification_sent = True
        except SlackApiError as e:
            logger.warning(f"Failed to send thread notification for {alarm_name}: {e.response['error']}", exc_info=True)
            # Non-critical, don't fail the entire operation
        except Exception as e:
            logger.warning(f"Unexpected error sending thread notification for {alarm_name}: {e}", exc_info=True)
            # Non-critical, don't fail the entire operation
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Successfully processed alarm recovery",
                "alarm": alarm_name,
                "alarm_reenabled": True,
                "slack_updated": slack_updated,
                "incident_closed": True,
                "notification_sent": notification_sent
            })
        }
    
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error", "details": str(e)})
        }
