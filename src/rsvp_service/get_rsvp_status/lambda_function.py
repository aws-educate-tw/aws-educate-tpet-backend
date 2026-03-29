import json


def lambda_handler(event, context):
    body = {
        "status": "success",
        "data": {
            "currentStatus": "PENDING",
            "participantName": "Wang Xiaoming",
            "runInfo": {
                "eventName": "AWS Cloud Workshop",
                "eventTime": "2026-03-01T09:00:00Z",
                "location": "Taipei 101",
                "registrationDeadline": "2026-02-20T23:59:59Z",
                "isRegistrationClosed": False,
            },
        },
    }
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }
