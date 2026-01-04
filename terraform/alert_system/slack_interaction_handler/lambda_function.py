import json
import os
import logging
import urllib.parse
import boto3
import base64
from slack_sdk import WebClient
from slack_util import handle_button_action
from alert_util import build_blocks
from incident_repository import IncidentRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cw = boto3.client("cloudwatch")
incident_repo = IncidentRepository()
slack = WebClient(token=os.environ["SLACK_BOT_TOKEN"])


def lambda_handler(event, context):
    """
    Handle Slack interactive components (button clicks) and URL verification.
    
    Returns:
        dict: Response with statusCode and body
            - 200: Successfully processed
            - 400: Invalid input/bad request
            - 404: Resource not found
            - 500: Server error
    """
    try:
        logger.info("=== Incoming Event ===")
        logger.info(json.dumps(event))
        
        # Validate event structure
        body = event.get("body")
        if not body:
            logger.warning("Empty body in request")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing request body"})
            }
        
        # Decode base64 if needed
        try:
            if event.get("isBase64Encoded", False):
                body = base64.b64decode(body).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to decode base64 body: {e}", exc_info=True)
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Failed to decode request body"})
            }
        
        # Parse URL-encoded parameters
        try:
            params = urllib.parse.parse_qs(body)
        except Exception as e:
            logger.error(f"Failed to parse URL-encoded body: {e}", exc_info=True)
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid request body format"})
            }
        
        # === Slack Button Interaction ===
        if "payload" in params:
            try:
                payload = json.loads(params["payload"][0])
                logger.info("Parsed Slack payload:")
                logger.info(json.dumps(payload))
            except (json.JSONDecodeError, IndexError) as e:
                logger.error(f"Failed to parse Slack payload: {e}", exc_info=True)
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid Slack payload format"})
                }
            
            # Validate payload structure
            if "actions" not in payload or not payload["actions"]:
                logger.error("Missing 'actions' in Slack payload")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid payload: missing actions"})
                }
            
            if "user" not in payload or "id" not in payload["user"]:
                logger.error("Missing user information in Slack payload")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid payload: missing user information"})
                }
            
            try:
                action = payload["actions"][0]
                action_id = action.get("action_id")
                alarm_name = action.get("value")
                user_id = payload["user"]["id"]
                
                if not action_id or not alarm_name:
                    logger.error(f"Missing action_id or alarm_name - action_id: {action_id}, alarm_name: {alarm_name}")
                    return {
                        "statusCode": 400,
                        "body": json.dumps({"error": "Invalid action: missing action_id or value"})
                    }
                
                logger.info(f"Processing action '{action_id}' for alarm '{alarm_name}' by user '{user_id}'")
                
            except (KeyError, IndexError) as e:
                logger.error(f"Failed to extract action details: {e}", exc_info=True)
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid action structure"})
                }
            
            # Get alarm description from CloudWatch
            description = "No description"
            try:
                alarm_details = cw.describe_alarms(AlarmNames=[alarm_name])
                if alarm_details.get("MetricAlarms"):
                    description = alarm_details["MetricAlarms"][0].get("AlarmDescription", "No description")
                    logger.info(f"Retrieved alarm description for {alarm_name}")
                else:
                    logger.warning(f"No metric alarms found for {alarm_name}")
            except cw.exceptions.ClientError as e:
                logger.error(f"CloudWatch API error getting alarm description: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Unexpected error getting alarm description: {e}", exc_info=True)
            
            # Get existing incident from DynamoDB
            try:
                item = incident_repo.get_incident(alarm_name)
            except Exception as e:
                logger.error(f"Failed to get incident for {alarm_name}: {e}", exc_info=True)
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "error": "Database error",
                        "alarm": alarm_name,
                        "details": str(e)
                    })
                }
            
            if not item:
                logger.warning(f"No incident found for {alarm_name}")
                return {
                    "statusCode": 404,
                    "body": json.dumps({
                        "error": "Incident not found",
                        "alarm": alarm_name
                    })
                }
            
            # Handle button action
            try:
                handle_button_action(
                    action_id=action_id,
                    alarm_name=alarm_name,
                    description=description,
                    user_id=user_id,
                    incident_item=item,
                    slack_client=slack,
                    cw_client=cw,
                    incident_repo=incident_repo,
                    build_blocks_func=build_blocks
                )
                logger.info(f"Successfully handled action '{action_id}' for {alarm_name}")
            except SlackApiError as e:
                logger.error(f"Slack API error handling action: {e.response['error']}", exc_info=True)
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "error": "Slack API error",
                        "details": e.response.get('error', 'Unknown error')
                    })
                }
            except Exception as e:
                logger.error(f"Failed to handle button action: {e}", exc_info=True)
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "error": "Failed to process action",
                        "alarm": alarm_name,
                        "action": action_id,
                        "details": str(e)
                    })
                }
            
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Action processed successfully",
                    "alarm": alarm_name,
                    "action": action_id
                })
            }
        
        # === Slack URL Verification ===
        try:
            data = json.loads(body)
            if data.get("type") == "url_verification":
                challenge = data.get("challenge")
                if not challenge:
                    logger.error("Missing challenge in URL verification request")
                    return {
                        "statusCode": 400,
                        "body": json.dumps({"error": "Missing challenge"})
                    }
                logger.info("Responding to Slack URL verification challenge")
                return {
                    "statusCode": 200,
                    "body": challenge
                }
        except json.JSONDecodeError:
            # Not JSON, continue to check other cases
            pass
        except Exception as e:
            logger.error(f"Error processing URL verification: {e}", exc_info=True)
        
        # Unknown request type
        logger.warning("Request ignored (no recognized payload type)")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Request acknowledged but not processed"})
        }
    
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error", "details": str(e)})
        }
