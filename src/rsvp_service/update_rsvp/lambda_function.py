import json
import os
from datetime import UTC, datetime

import boto3
import jwt
from botocore.exceptions import ClientError

dynamodb = boto3.client("dynamodb")
TABLE_NAME = os.environ.get("PARTICIPANT_TABLE", "participant")
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key")


def lambda_handler(event, context):
    try:
        auth_header = event.get("headers", {}).get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return build_response(401, {"code": "INVALID_TOKEN"})

        token = auth_header.split(" ")[1]
        try:
            decoded_token = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            email_id = decoded_token.get("email")
            campaign_id = decoded_token.get("campaign_id")
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return build_response(401, {"code": "INVALID_TOKEN"})

        path_param = event.get("pathParameters", {}).get("run_id_participant_id", "")
        if "_" not in path_param:
            return build_response(400, {"code": "INVALID_PATH_FORMAT"})

        run_id, participant_id = path_param.split("_", 1)

        body = json.loads(event.get("body", "{}"))
        action = body.get("action")
        client_time = body.get("client_time")

        if action not in ["ATTEND", "NOT_ATTEND"] or not client_time:
            return build_response(400, {"code": "INVALID_PAYLOAD"})

        response = dynamodb.get_item(
            TableName=TABLE_NAME,
            Key={"run_id": {"S": run_id}, "participant_id": {"S": participant_id}},
            ConsistentRead=True,
        )
        db_item = response.get("Item")

        old_read_ts = None

        if db_item:
            db_client_time = db_item.get("client_time", {}).get("S", "")
            db_status = db_item.get("rsvp_status", {}).get("S", "PENDING")

            if client_time < db_client_time:
                return build_response(200, {"data": {"currentStatus": db_status}})

            old_read_ts = db_client_time

        updated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        new_item = {
            "run_id": {"S": run_id},
            "participant_id": {"S": participant_id},
            "email": {"S": email_id},
            "campaign_id": {"S": campaign_id},
            "rsvp_status": {"S": action},
            "client_time": {"S": client_time},
            "updated_at": {"S": updated_at},
            "campaign_participant_uniq_handle": {"S": f"{campaign_id}_{email_id}"},
        }

        if not db_item:
            new_item["created_at"] = {"S": updated_at}
            condition = "attribute_not_exists(participant_id)"
        else:
            new_item["created_at"] = db_item["created_at"]
            condition = "client_time = :old_ts"

        transact_params = {
            "TransactItems": [
                {
                    "Put": {
                        "TableName": TABLE_NAME,
                        "Item": new_item,
                        "ConditionExpression": condition,
                    }
                }
            ]
        }

        if db_item:
            transact_params["TransactItems"][0]["Put"]["ExpressionAttributeValues"] = {
                ":old_ts": {"S": old_read_ts}
            }

        dynamodb.transact_write_items(**transact_params)

        return build_response(
            200, {"status": "SUCCESS", "data": {"currentStatus": action}}
        )

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "TransactionCanceledException":
            return build_response(409, {"code": "CONCURRENT_UPDATE"})
        print(f"AWS Error: {e}")
        return build_response(500, {"code": "INTERNAL_ERROR"})

    except Exception as e:
        print(f"System Error: {e}")
        return build_response(500, {"code": "INTERNAL_ERROR"})


def build_response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body_dict),
    }
