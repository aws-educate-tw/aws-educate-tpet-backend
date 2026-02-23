def build_blocks(alarm_name, description, state, chart_url=None):
    if state == "ALARM":
        color = "#FF0000"
        emoji = "🚨"
        status = "ALARM"
        buttons = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Acknowledge"},
                "action_id": "acknowledge_button",
                "value": alarm_name,
                "style": "primary",
            }
        ]
    elif state == "ACKNOWLEDGED":
        color = "#FFA500"
        emoji = "👀"
        status = "ACKNOWLEDGED"
        buttons = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Unacknowledge"},
                "action_id": "unacknowledge_button",
                "value": alarm_name,
            }
        ]
    elif state == "RESOLVED":
        color = "#36A64F"
        emoji = "✅"
        status = "RESOLVED"
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
