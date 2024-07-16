import json

import boto3
from botocore.exceptions import ClientError


def lambda_handler(event, context):
    client = boto3.client("cognito-idp")
    try:
        # 解析 event['body'] 為字典
        body = json.loads(event["body"])

        response = client.initiate_auth(
            ClientId="4hu6irac6o43n9ug67o6a9vahk",
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": body["username"], "PASSWORD": body["password"]},
        )
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "access_token": response["AuthenticationResult"]["AccessToken"],
                    "id_token": response["AuthenticationResult"]["IdToken"],
                    "refresh_token": response["AuthenticationResult"]["RefreshToken"],
                }
            ),
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
