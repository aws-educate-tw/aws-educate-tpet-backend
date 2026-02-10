import json

def lambda_handler(event, context):
    # TODO: Implement FINAL_FLUSH sync to Aurora
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "sync_aurora placeholder",
            "received": event,
        }),
    }
