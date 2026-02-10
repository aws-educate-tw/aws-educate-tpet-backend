import json
import os
from datetime import datetime, timezone


def lambda_handler(event, context):
    # TODO: Implement RSVP snapshot logic
    now = datetime.now(timezone.utc).isoformat()
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
