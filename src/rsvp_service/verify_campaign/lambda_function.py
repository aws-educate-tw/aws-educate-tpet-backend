import json


def lambda_handler(event, context):
    body = {
        "status": "success",
        "data": {
            "isValid": True,
            "Campaign_id": "evt_uuid_1001",
            "Campaign_name": "Global Developer Conference 2026",
            "is_active": True,
        },
    }
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }
