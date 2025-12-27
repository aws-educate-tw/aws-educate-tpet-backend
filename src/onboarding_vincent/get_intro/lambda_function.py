import json

def lambda_handler(event, context):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "name": "Vincent",
            "introduction": "Hi, I'm Vincent. Nice to meet you"
        })
    }
