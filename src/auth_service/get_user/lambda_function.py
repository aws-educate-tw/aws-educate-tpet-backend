import json

import boto3
from botocore.exceptions import ClientError


def lambda_handler(event, context):
    client = boto3.client("cognito-idp")

    user_id = event["pathParameters"]["user_id"]
    user_pool_id = "us-west-2_SLeq1xRmU"

    try:
        response = client.admin_get_user(UserPoolId=user_pool_id, Username=user_id)

        user_attributes = {
            attr["Name"]: attr["Value"] for attr in response["UserAttributes"]
        }

        return {
            "statusCode": 200,
            "body": json.dumps({"user_id": user_id, "attributes": user_attributes}),
            "headers": {"Content-Type": "application/json"},
        }

    except ClientError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"},
        }
