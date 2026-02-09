import json
import os
from datetime import UTC, datetime


def lambda_handler(event, context):
    # TODO: Implement RSVP status query logic
    now = datetime.now(UTC).isoformat()
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(
            {
                "message": "rsvp_status_query placeholder",
                "timestamp": now,
                "environment": os.getenv("ENVIRONMENT"),
                "service": os.getenv("SERVICE"),
                "event": event,
            }
        ),
    }
