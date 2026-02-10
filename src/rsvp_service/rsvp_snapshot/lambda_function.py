import json
import os
from datetime import UTC, datetime


def lambda_handler(event, context):
    # TODO: Implement RSVP snapshot logic
    now = datetime.now(UTC).isoformat()
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(
            {
                "message": "rsvp_snapshot placeholder",
                "timestamp": now,
                "environment": os.getenv("ENVIRONMENT"),
                "service": os.getenv("SERVICE"),
                "event": event,
            }
        ),
    }
