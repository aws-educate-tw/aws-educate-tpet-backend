import json
import logging
import os

from cloudwatch_util import CloudWatchError, get_metric_chart
from incident_repository import IncidentRepository
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from utils import build_blocks, post_incident_message

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = os.environ["SLACK_CHANNEL"]

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.info(f"Token prefix: {SLACK_BOT_TOKEN[:4]}")

incident_repo = IncidentRepository()
slack = WebClient(token=SLACK_BOT_TOKEN)


def map_incident_state(cw_state):
    if cw_state == "ALARM":
        return "ALARM"
    if cw_state == "INSUFFICIENT_DATA":
        return None
    if cw_state == "OK":
        return "RESOLVED"
    return cw_state


def lambda_handler(event, context):
    """
    Process SNS notifications from CloudWatch Alarms and manage incidents in Slack.

    Returns:
        dict: Response with statusCode and body
            - 200: All records processed successfully
            - 207: Multi-Status (some records failed)
            - 400: Invalid input/bad request
            - 500: Complete failure
    """
    try:
        logger.info("=== Incoming Event ===")
        logger.info(json.dumps(event))

        # Validate event structure
        if "Records" not in event:
            logger.error("Missing 'Records' in event")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"error": "Invalid event structure: missing 'Records'"}
                ),
            }

        total_records = len(event["Records"])
        failed_records = []

        for idx, record in enumerate(event["Records"]):
            try:
                logger.info(f"Processing record {idx + 1}/{total_records}")

                # Parse SNS message
                try:
                    msg = json.loads(record["Sns"]["Message"])
                except (KeyError, json.JSONDecodeError) as e:
                    logger.error(f"Failed to parse SNS message: {e}", exc_info=True)
                    failed_records.append(
                        {"index": idx, "error": "Invalid SNS message format"}
                    )
                    continue

                # Extract required fields
                alarm_name = msg.get("AlarmName")
                raw_state = msg.get("NewStateValue")

                if not alarm_name or not raw_state:
                    logger.error(
                        f"Missing required fields - AlarmName: {alarm_name}, NewStateValue: {raw_state}"
                    )
                    failed_records.append(
                        {"index": idx, "error": "Missing required alarm fields"}
                    )
                    continue

                incident_state = map_incident_state(raw_state)
                if incident_state is None:
                    logger.info(
                        f"Skipping INSUFFICIENT_DATA for alarm {alarm_name} (no incident update)"
                    )
                    continue
                description = msg.get("AlarmDescription", "No description")
                trigger_info = msg.get("Trigger", {})

                # Get existing incident from DynamoDB
                try:
                    item = incident_repo.get_incident(alarm_name)
                except Exception as e:
                    logger.error(
                        f"Failed to get incident for {alarm_name}: {e}", exc_info=True
                    )
                    failed_records.append(
                        {"index": idx, "error": "Database error", "alarm": alarm_name}
                    )
                    continue

                # Generate CloudWatch chart (non-critical, continue on failure)
                chart_data = None
                try:
                    chart_data = get_metric_chart(trigger_info)
                    logger.info(f"Generated CloudWatch chart for {alarm_name}")
                except CloudWatchError as e:
                    logger.warning(
                        f"CloudWatch chart generation failed (status {e.status_code}): {e.message}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Unexpected error generating chart: {e}", exc_info=True
                    )

                blocks, color = build_blocks(
                    alarm_name, description, incident_state, None
                )

                # === CASE 1: new incident ===
                if not item or not item.get("incident_open", False):
                    if incident_state == "RESOLVED":
                        logger.info(
                            f"Skipping RESOLVED state for non-existent incident: {alarm_name}"
                        )
                        continue

                    # Post incident message to Slack
                    try:
                        slack_ts = post_incident_message(
                            slack_client=slack,
                            channel=SLACK_CHANNEL,
                            alarm_name=alarm_name,
                            incident_state=incident_state,
                            blocks=blocks,
                            color=color,
                            chart_data=chart_data,
                        )
                    except SlackApiError as e:
                        logger.error(
                            f"Slack API error posting message for {alarm_name}: {e.response['error']}",
                            exc_info=True,
                        )
                        failed_records.append(
                            {
                                "index": idx,
                                "error": "Slack API error",
                                "alarm": alarm_name,
                            }
                        )
                        continue
                    except Exception as e:
                        logger.error(
                            f"Failed to post Slack message for {alarm_name}: {e}",
                            exc_info=True,
                        )
                        failed_records.append(
                            {
                                "index": idx,
                                "error": "Slack posting failed",
                                "alarm": alarm_name,
                            }
                        )
                        continue

                    # Create new incident in DynamoDB
                    try:
                        incident_repo.create_incident(
                            alarm_name=alarm_name,
                            slack_channel=SLACK_CHANNEL,
                            slack_ts=slack_ts,
                            incident_state=incident_state,
                        )
                        logger.info(f"Created new incident for {alarm_name}")
                    except Exception as e:
                        logger.error(
                            f"Failed to create incident in DynamoDB for {alarm_name}: {e}",
                            exc_info=True,
                        )
                        # Incident was posted to Slack but not saved to DB - log as warning
                        logger.warning(
                            f"Incident {alarm_name} posted to Slack but not saved to DynamoDB"
                        )
                        failed_records.append(
                            {
                                "index": idx,
                                "error": "Database write failed",
                                "alarm": alarm_name,
                            }
                        )

                    continue

                # === CASE 2: update existing incident ===
                summary_text = f"[{incident_state}] {alarm_name}"

                # Update Slack message
                try:
                    slack.chat_update(
                        channel=item["slack_channel"],
                        ts=item["slack_ts"],
                        text=summary_text,
                        attachments=[{"color": color, "blocks": blocks}],
                    )
                    logger.info(
                        f"Updated Slack message for {alarm_name} to state {incident_state}"
                    )
                except SlackApiError as e:
                    logger.error(
                        f"Slack API error updating message for {alarm_name}: {e.response['error']}",
                        exc_info=True,
                    )
                    # Continue to update DynamoDB even if Slack update fails
                except Exception as e:
                    logger.error(
                        f"Failed to update Slack message for {alarm_name}: {e}",
                        exc_info=True,
                    )
                    # Continue to update DynamoDB even if Slack update fails

                # Update DynamoDB
                try:
                    if incident_state == "RESOLVED":
                        incident_repo.close_incident(alarm_name, incident_state)
                        logger.info(f"Closed incident for {alarm_name}")
                    else:
                        incident_repo.update_incident_state(alarm_name, incident_state)
                        logger.info(
                            f"Updated incident state for {alarm_name} to {incident_state}"
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to update incident in DynamoDB for {alarm_name}: {e}",
                        exc_info=True,
                    )
                    failed_records.append(
                        {
                            "index": idx,
                            "error": "Database update failed",
                            "alarm": alarm_name,
                        }
                    )

            except Exception as e:
                logger.error(
                    f"Unexpected error processing record {idx}: {e}", exc_info=True
                )
                failed_records.append({"index": idx, "error": str(e)})

        # Determine response based on success/failure counts
        if not failed_records:
            logger.info(f"Successfully processed all {total_records} records")
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "All records processed successfully",
                        "total": total_records,
                        "succeeded": total_records,
                    }
                ),
            }
        elif len(failed_records) < total_records:
            logger.warning(
                f"Partial success: {total_records - len(failed_records)}/{total_records} records processed"
            )
            return {
                "statusCode": 207,
                "body": json.dumps(
                    {
                        "message": "Partial success",
                        "total": total_records,
                        "succeeded": total_records - len(failed_records),
                        "failed": len(failed_records),
                        "failures": failed_records,
                    }
                ),
            }
        else:
            logger.error(f"All {total_records} records failed")
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "error": "All records failed",
                        "total": total_records,
                        "failures": failed_records,
                    }
                ),
            }

    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error", "details": str(e)}),
        }
