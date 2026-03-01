import json
import logging
import os

from cloudwatch_util import CloudWatchError, get_metric_chart
from incident_repository import IncidentRepository
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from utils import CloudWatchAlarmState, IncidentState, build_blocks, post_incident_message

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = os.environ["SLACK_CHANNEL"]

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.info("Token prefix: %s", SLACK_BOT_TOKEN[:4])

incident_repo = IncidentRepository()
slack = WebClient(token=SLACK_BOT_TOKEN)


def map_incident_state(cw_state):
    """
    Map CloudWatch alarm state to incident state.

    Args:
        cw_state: CloudWatch alarm state value

    Returns:
        str: Mapped incident state or None for INSUFFICIENT_DATA
    """
    if cw_state == CloudWatchAlarmState.ALARM.value:
        return IncidentState.ALARM.value
    if cw_state == CloudWatchAlarmState.INSUFFICIENT_DATA.value:
        return None
    if cw_state == CloudWatchAlarmState.OK.value:
        return IncidentState.RESOLVED.value
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
                logger.info("Processing record %s/%s", idx + 1, total_records)

                # Parse SNS message
                try:
                    msg = json.loads(record["Sns"]["Message"])
                except (KeyError, json.JSONDecodeError) as e:
                    logger.error("Failed to parse SNS message: %s", e, exc_info=True)
                    failed_records.append(
                        {"index": idx, "error": "Invalid SNS message format"}
                    )
                    continue

                # Extract required fields
                alarm_name = msg.get("AlarmName")
                raw_state = msg.get("NewStateValue")

                if not alarm_name or not raw_state:
                    logger.error(
                        "Missing required fields - AlarmName: %s, NewStateValue: %s",
                        alarm_name,
                        raw_state,
                    )
                    failed_records.append(
                        {"index": idx, "error": "Missing required alarm fields"}
                    )
                    continue

                incident_state = map_incident_state(raw_state)
                if incident_state is None:
                    logger.info(
                        "Skipping INSUFFICIENT_DATA for alarm %s (no incident update)",
                        alarm_name,
                    )
                    continue
                description = msg.get("AlarmDescription", "No description")
                trigger_info = msg.get("Trigger", {})

                # Get existing incident from DynamoDB
                try:
                    item = incident_repo.get_incident(alarm_name)
                except Exception as e:
                    logger.error(
                        "Failed to get incident for %s: %s",
                        alarm_name,
                        e,
                        exc_info=True,
                    )
                    failed_records.append(
                        {"index": idx, "error": "Database error", "alarm": alarm_name}
                    )
                    continue

                # Generate CloudWatch chart (non-critical, continue on failure)
                chart_data = None
                try:
                    chart_data = get_metric_chart(trigger_info)
                    logger.info("Generated CloudWatch chart for %s", alarm_name)
                except CloudWatchError as e:
                    logger.warning(
                        "CloudWatch chart generation failed (status %s): %s",
                        e.status_code,
                        e.message,
                    )
                except Exception as e:
                    logger.warning(
                        "Unexpected error generating chart: %s", e, exc_info=True
                    )

                blocks, color = build_blocks(
                    alarm_name, description, incident_state, None
                )

                # === CASE 1: new incident ===
                if not item or not item.get("incident_open", False):
                    if incident_state == IncidentState.RESOLVED.value:
                        logger.info(
                            "Skipping RESOLVED state for non-existent incident: %s",
                            alarm_name,
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
                            "Slack API error posting message for %s: %s",
                            alarm_name,
                            e.response['error'],
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
                            "Failed to post Slack message for %s: %s",
                            alarm_name,
                            e,
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
                        logger.info("Created new incident for %s", alarm_name)
                    except Exception as e:
                        logger.error(
                            "Failed to create incident in DynamoDB for %s: %s",
                            alarm_name,
                            e,
                            exc_info=True,
                        )
                        # Incident was posted to Slack but not saved to DB - log as warning
                        logger.warning(
                            "Incident %s posted to Slack but not saved to DynamoDB",
                            alarm_name,
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
                        "Updated Slack message for %s to state %s",
                        alarm_name,
                        incident_state,
                    )
                except SlackApiError as e:
                    logger.error(
                        "Slack API error updating message for %s: %s",
                        alarm_name,
                        e.response['error'],
                        exc_info=True,
                    )
                    # Continue to update DynamoDB even if Slack update fails
                except Exception as e:
                    logger.error(
                        "Failed to update Slack message for %s: %s",
                        alarm_name,
                        e,
                        exc_info=True,
                    )
                    # Continue to update DynamoDB even if Slack update fails

                # Update DynamoDB
                try:
                    if incident_state == IncidentState.RESOLVED.value:
                        incident_repo.close_incident(alarm_name, incident_state)
                        logger.info("Closed incident for %s", alarm_name)
                    else:
                        incident_repo.update_incident_state(alarm_name, incident_state)
                        logger.info(
                            "Updated incident state for %s to %s",
                            alarm_name,
                            incident_state,
                        )
                except Exception as e:
                    logger.error(
                        "Failed to update incident in DynamoDB for %s: %s",
                        alarm_name,
                        e,
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
                    "Unexpected error processing record %s: %s", idx, e, exc_info=True
                )
                failed_records.append({"index": idx, "error": str(e)})

        # Determine response based on success/failure counts
        if not failed_records:
            logger.info("Successfully processed all %s records", total_records)
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
                "Partial success: %s/%s records processed",
                total_records - len(failed_records),
                total_records,
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
            logger.error("All %s records failed", total_records)
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
        logger.error("Unexpected error in lambda_handler: %s", e, exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error", "details": str(e)}),
        }
