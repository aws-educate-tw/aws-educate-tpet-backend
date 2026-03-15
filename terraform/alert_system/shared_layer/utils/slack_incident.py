import logging

from slack_sdk.errors import SlackApiError

from .alarm_state_enum import IncidentState

logger = logging.getLogger()


def post_incident_message(
    slack_client, channel, alarm_name, incident_state, blocks, color, chart_data=None
):
    """
    Post a new incident message to Slack with optional chart attachment.

    Args:
        slack_client: Slack WebClient instance
        channel: Slack channel ID or name
        alarm_name: Name of the alarm
        incident_state: Current state of the incident (ALARM, ACKNOWLEDGED, RESOLVED)
        blocks: Slack message blocks
        color: Attachment color
        chart_data: Optional dict with chart image data {"data": bytes, "filename": str, "title": str}

    Returns:
        str: Message timestamp (ts) of the posted message
    """
    try:
        message_text = f"[{incident_state}] {alarm_name}"

        if chart_data:
            # First, post a message with blocks and color
            result = slack_client.chat_postMessage(
                channel=channel,
                text=message_text,
                attachments=[{"color": color, "blocks": blocks}],
            )
            slack_ts = result["ts"]
            logger.info("Posted incident message for %s", alarm_name)

            # Then upload the chart image to the same thread
            slack_client.files_upload_v2(
                channel=channel,
                thread_ts=slack_ts,
                file=chart_data["data"],
                filename=chart_data["filename"],
                title=chart_data["title"],
                request_file_info=False,
            )
            logger.info("Uploaded chart to thread for %s", alarm_name)
        else:
            # Post message without chart
            result = slack_client.chat_postMessage(
                channel=channel,
                text=message_text,
                attachments=[{"color": color, "blocks": blocks}],
            )
            slack_ts = result["ts"]
            logger.info("Posted incident message for %s", alarm_name)

        return slack_ts

    except SlackApiError as e:
        logger.error(
            "Failed to post incident message: %s",
            e.response["error"],
            exc_info=True,
        )
        raise
    except Exception as e:
        logger.error("Unexpected error posting incident message: %s", e, exc_info=True)
        raise


def update_incident_message(
    slack_client, channel, ts, alarm_name, incident_state, blocks, color
):
    """
    Update an existing incident message in Slack.

    Args:
        slack_client: Slack WebClient instance
        channel: Slack channel ID or name
        ts: Message timestamp to update
        alarm_name: Name of the alarm
        incident_state: Current state of the incident
        blocks: Updated Slack message blocks
        color: Updated attachment color
    """
    try:
        message_text = f"[{incident_state}] {alarm_name}"

        slack_client.chat_update(
            channel=channel,
            ts=ts,
            text=message_text,
            attachments=[{"color": color, "blocks": blocks}],
        )

        logger.info(
            "Updated incident message for %s to state %s",
            alarm_name,
            incident_state,
        )

    except SlackApiError as e:
        logger.error(
            "Failed to update incident message: %s",
            e.response["error"],
            exc_info=True,
        )
        raise
    except Exception as e:
        logger.error("Unexpected error updating incident message: %s", e, exc_info=True)
        raise


def post_thread_message(slack_client, channel, thread_ts, message):
    """
    Post a message to a Slack thread.

    Args:
        slack_client: Slack WebClient instance
        channel: Slack channel ID or name
        thread_ts: Thread timestamp to reply to
        message: Message text to post

    Returns:
        dict: Slack API response
    """
    try:
        result = slack_client.chat_postMessage(
            channel=channel, thread_ts=thread_ts, text=message
        )

        logger.info("Posted thread message to channel %s", channel)
        return result

    except SlackApiError as e:
        logger.error(
            "Failed to post thread message: %s", e.response["error"], exc_info=True
        )
        raise
    except Exception as e:
        logger.error("Unexpected error posting thread message: %s", e, exc_info=True)
        raise


def handle_button_action(
    action_id,
    alarm_name,
    description,
    user_id,
    incident_item,
    slack_client,
    cw_client,
    incident_repo,
    build_blocks_func,
):
    """
    Handle Slack button interactions for alarm acknowledgment.

    Args:
        action_id: Button action ID (acknowledge_button or unacknowledge_button)
        alarm_name: Name of the alarm
        description: Alarm description
        user_id: Slack user ID who clicked the button
        incident_item: Incident data from DynamoDB
        slack_client: Slack WebClient instance
        cw_client: CloudWatch boto3 client
        incident_repo: IncidentRepository instance
        build_blocks_func: Function to build Slack message blocks
    """
    try:
        if action_id == "acknowledge_button":
            # Disable alarm actions to prevent auto-recovery
            cw_client.disable_alarm_actions(AlarmNames=[alarm_name])

            incident_state = IncidentState.ACKNOWLEDGED.value
            logger.info("%s -> ACKNOWLEDGED (actions disabled)", alarm_name)

            # Update Slack message
            blocks, color = build_blocks_func(alarm_name, description, incident_state)
            update_incident_message(
                slack_client=slack_client,
                channel=incident_item["slack_channel"],
                ts=incident_item["slack_ts"],
                alarm_name=alarm_name,
                incident_state=incident_state,
                blocks=blocks,
                color=color,
            )

            # Update DynamoDB
            incident_repo.update_incident_state(alarm_name, incident_state)

            # Send thread notification
            message = f"<@{user_id}> acknowledged this alarm and will handle this incident. 👀"
            post_thread_message(
                slack_client=slack_client,
                channel=incident_item["slack_channel"],
                thread_ts=incident_item["slack_ts"],
                message=message,
            )

        elif action_id == "unacknowledge_button":
            # Enable alarm actions
            cw_client.enable_alarm_actions(AlarmNames=[alarm_name])

            incident_state = IncidentState.ALARM.value
            logger.info("%s -> ALARM (actions enabled)", alarm_name)

            # Update Slack message
            blocks, color = build_blocks_func(alarm_name, description, incident_state)
            update_incident_message(
                slack_client=slack_client,
                channel=incident_item["slack_channel"],
                ts=incident_item["slack_ts"],
                alarm_name=alarm_name,
                incident_state=incident_state,
                blocks=blocks,
                color=color,
            )

            # Update DynamoDB
            incident_repo.update_incident_state(alarm_name, incident_state)

            # Send thread notification
            message = f"<@{user_id}> unacknowledged this alarm. 🚨"
            post_thread_message(
                slack_client=slack_client,
                channel=incident_item["slack_channel"],
                thread_ts=incident_item["slack_ts"],
                message=message,
            )

        else:
            logger.warning("Unknown action_id: %s", action_id)

    except Exception as e:
        logger.error(
            "Failed to handle button action %s: %s", action_id, e, exc_info=True
        )
        raise
