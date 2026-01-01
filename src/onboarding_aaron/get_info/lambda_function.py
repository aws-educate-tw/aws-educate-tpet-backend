import json


def lambda_handler(event, context):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "first name": "Aaron",
                "last name": "Chen",
                "college": "NCU",
                "year": "junior",
                "position": "backend",
            }
        ),
    }
