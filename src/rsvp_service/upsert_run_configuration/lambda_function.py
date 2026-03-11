import json


def lambda_handler(event, context):
    body = {
        "run_id": "run_uuid_a1b2",
        "participant_id": "pp_123",
        "email": "test@gmail.com",
        "campaign_id": "cp_123",
        "name": "Wang Xiaoming",
        "campaign_participant_uniq_handle": "cp_123#shiun@gmail.com",
    }
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }
