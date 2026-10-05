from .alarm_state_enum import IncidentState


def build_blocks(alarm_name, description, state, chart_url=None):
    """
    Build Slack message blocks for alarm incidents.

    Args:
        alarm_name: Name of the alarm
        description: Alarm description text
        state: Incident state (ALARM, ACKNOWLEDGED, RESOLVED)
        chart_url: Optional URL to CloudWatch metric chart

    Returns:
        tuple: (blocks, color) - Slack message blocks and attachment color
    """
    try:
        incident_state = IncidentState(state)
    except ValueError:
        incident_state = None

    if incident_state == IncidentState.ALARM:
        color = "#FF0000"
        emoji = "🚨"
        status = IncidentState.ALARM.value
        buttons = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Acknowledge"},
                "action_id": "acknowledge_button",
                "value": alarm_name,
                "style": "primary",
            }
        ]
    elif incident_state == IncidentState.ACKNOWLEDGED:
        color = "#FFA500"
        emoji = "👀"
        status = IncidentState.ACKNOWLEDGED.value
        buttons = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Unacknowledge"},
                "action_id": "unacknowledge_button",
                "value": alarm_name,
            }
        ]
    elif incident_state == IncidentState.RESOLVED:
        color = "#36A64F"
        emoji = "✅"
        status = IncidentState.RESOLVED.value
        buttons = []
    else:
        color = "#439FE0"
        emoji = "ℹ️"
        status = state
        buttons = []

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{description}*"}},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Alarm*\n{alarm_name}"},
                {"type": "mrkdwn", "text": f"*Status*\n{emoji} {status}"},
            ],
        },
    ]

    # Add chart image if available
    if chart_url:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{chart_url}|📊 View CloudWatch Metric Chart>",
                },
            }
        )

    if buttons:
        blocks.append({"type": "actions", "elements": buttons})

    return blocks, color
