import json

def lambda_handler(event, context):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "name": "Seren",
            "introduction": "Hello! I'm Seren! Nice to meet you all!"
        })
    }