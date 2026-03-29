import json


def lambda_handler(event, context):
    body = {
        "status": "success",
        "data": {
            "action": "ATTEND",
            "clientTimestamp": 1705821234567,
        },
    }
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }
