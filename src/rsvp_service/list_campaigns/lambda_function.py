import json


def lambda_handler(event, context):
    body = [
        {
            "campaign_id": "evt_uuid_1001",
            "campaign_name": "Global Developer Conference 2026",
            "campaign_start_time": "2026-05-20T09:00:00Z",
            "campaign_end_time": "2026-05-25T09:00:00Z",
            "campaign_location": "",
            "campaign_created_at": "2026-01-10T10:00:00Z",
            "is_active": True,
        },
        {
            "campaign_id": "evt_uuid_1002",
            "campaign_name": "AI Workshop 2026",
            "campaign_start_time": "2026-05-20T09:00:00Z",
            "campaign_end_time": "2026-05-25T09:00:00Z",
            "campaign_location": "",
            "campaign_created_at": "2026-01-10T10:00:00Z",
            "is_active": True,
        },
    ]
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }
