import json

import boto3
from botocore.exceptions import ClientError


def lambda_handler(event, context):
    client = boto3.client("cognito-idp")
    try:
        body = json.loads(event["body"])
        response = client.initiate_auth(
            ClientId="4hu6irac6o43n9ug67o6a9vahk",
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": body["username"], "PASSWORD": body["password"]},
        )
        access_token = response["AuthenticationResult"]["AccessToken"]
        return {
            "statusCode": 200,
            "headers": {
                "Set-Cookie": f"accessToken={access_token}; Path=/; Secure; HttpOnly; SameSite=None; Domain=.awseducate.systems"
            },
            "body": json.dumps({"message": "Login successful"}),
        }
    except ClientError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": e.response["Error"]["Message"]}),
        }
    except json.JSONDecodeError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid JSON format in request body"}),
        }
