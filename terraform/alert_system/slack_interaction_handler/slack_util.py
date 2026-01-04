import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger()


def post_incident_message(slack_client, channel, alarm_name, incident_state, blocks, color, chart_data=None):
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
            # Post message with chart image
            result = slack_client.files_upload_v2(
                channel=channel,
                file=chart_data["data"],
                filename=chart_data["filename"],
                title=chart_data["title"],
                initial_comment=message_text,
                request_file_info=False
            )
            # Get the message timestamp from the file upload
            slack_ts = result["file"]["shares"]["public"][channel][0]["ts"]
            logger.info(f"Posted incident message with chart for {alarm_name}")
        else:
            # Post message without chart
            result = slack_client.chat_postMessage(
                channel=channel,
                text=message_text,
                attachments=[{"color": color, "blocks": blocks}]
            )
            slack_ts = result["ts"]
            logger.info(f"Posted incident message for {alarm_name}")
        
        # Update the message with blocks (if chart was uploaded, add the blocks now)
        if chart_data:
            slack_client.chat_update(
                channel=channel,
                ts=slack_ts,
                text=message_text,
                attachments=[{"color": color, "blocks": blocks}]
            )
        
        return slack_ts
        
    except SlackApiError as e:
        logger.error(f"Failed to post incident message: {e.response['error']}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error posting incident message: {e}", exc_info=True)
        raise


def update_incident_message(slack_client, channel, ts, alarm_name, incident_state, blocks, color):
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
            attachments=[{"color": color, "blocks": blocks}]
        )
        
        logger.info(f"Updated incident message for {alarm_name} to state {incident_state}")
        
    except SlackApiError as e:
        logger.error(f"Failed to update incident message: {e.response['error']}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating incident message: {e}", exc_info=True)
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
            channel=channel,
            thread_ts=thread_ts,
            text=message
        )
        
        logger.info(f"Posted thread message to channel {channel}")
        return result
        
    except SlackApiError as e:
        logger.error(f"Failed to post thread message: {e.response['error']}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error posting thread message: {e}", exc_info=True)
        raise


def handle_button_action(action_id, alarm_name, description, user_id, incident_item, 
                         slack_client, cw_client, incident_repo, build_blocks_func):
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
            
            incident_state = "ACKNOWLEDGED"
            logger.info(f"{alarm_name} -> ACKNOWLEDGED (actions disabled)")
            
            # Update Slack message
            blocks, color = build_blocks_func(alarm_name, description, incident_state)
            update_incident_message(
                slack_client=slack_client,
                channel=incident_item["slack_channel"],
                ts=incident_item["slack_ts"],
                alarm_name=alarm_name,
                incident_state=incident_state,
                blocks=blocks,
                color=color
            )
            
            # Update DynamoDB
            incident_repo.update_incident_state(alarm_name, incident_state)
            
            # Send thread notification
            message = f"<@{user_id}> acknowledged this alarm and will handle this incident. 👀"
            post_thread_message(
                slack_client=slack_client,
                channel=incident_item["slack_channel"],
                thread_ts=incident_item["slack_ts"],
                message=message
            )
            
        elif action_id == "unacknowledge_button":
            # Enable alarm actions
            cw_client.enable_alarm_actions(AlarmNames=[alarm_name])
            
            incident_state = "ALARM"
            logger.info(f"{alarm_name} -> ALARM (actions enabled)")
            
            # Update Slack message
            blocks, color = build_blocks_func(alarm_name, description, incident_state)
            update_incident_message(
                slack_client=slack_client,
                channel=incident_item["slack_channel"],
                ts=incident_item["slack_ts"],
                alarm_name=alarm_name,
                incident_state=incident_state,
                blocks=blocks,
                color=color
            )
            
            # Update DynamoDB
            incident_repo.update_incident_state(alarm_name, incident_state)
            
            # Send thread notification
            message = f"<@{user_id}> unacknowledged this alarm. 🚨"
            post_thread_message(
                slack_client=slack_client,
                channel=incident_item["slack_channel"],
                thread_ts=incident_item["slack_ts"],
                message=message
            )
            
        else:
            logger.warning(f"Unknown action_id: {action_id}")
            
    except Exception as e:
        logger.error(f"Failed to handle button action {action_id}: {e}", exc_info=True)
        raise