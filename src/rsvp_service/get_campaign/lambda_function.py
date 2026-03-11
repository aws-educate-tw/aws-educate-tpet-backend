import json


def lambda_handler(event, context):
    body = {
        "campaign_id": "evt_uuid_1001",
        "campaign_name": "Global Developer Conference 2026",
        "description": "Annual flagship tech event",
        "created_at": "2026-01-01T00:00:00Z",
        "is_active": True,
        "runs": [
            {
                "run_id": "run_uuid_a1b2",
                "subject": "workshop confirmation 1",
                "registration_deadline": "2026-02-20T23:59:59Z",
                "max_participants": 100,
                "is_active": True,
                "participants": [
                    {
                        "participant_id": "user_uuid_555",
                        "email_id": "email_uuid_999",
                        "rsvp_status": "ATTEND",
                        "name": "Wang Xiaoming",
                        "created_at": "2026-01-15T08:30:00Z",
                        "updated_at": "2026-02-20T14:22:10Z",
                    }
                ],
            },
            {
                "run_id": "run_uuid_c3d4",
                "subject": "workshop confirmation 2",
                "registration_deadline": "2026-02-21T23:59:59Z",
                "max_participants": 100,
                "is_active": True,
                "participants": [],
            },
        ],
    }
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }
