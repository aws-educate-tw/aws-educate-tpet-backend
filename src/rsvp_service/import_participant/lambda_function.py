import json


def lambda_handler(event, context):
    body = {
        "status": "SUCCESS",
        "participant_id": "uuid_550e",
    }
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }
