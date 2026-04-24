import json
import boto3
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

dynamodb = boto3.resource('dynamodb')
RUN_TABLE_NAME = os.environ.get('CAMPAIGN_RUN_TABLE') 
PARTICIPANT_TABLE_NAME = os.environ.get('PARTICIPANT_TABLE')   

def get_item(table_name, key):
    table = dynamodb.Table(table_name)
    return table.get_item(Key=key).get('Item')

def lambda_handler(event, context):
    try:
        authorizer = event.get('requestContext', {}).get('authorizer', {}).get('lambda', {})
        campaign_id = authorizer.get('campaign_id')
        token_name = authorizer.get('name', '未知使用者')
        
        path_params = event.get('pathParameters', {})
        run_id_participant_id = path_params.get('run_id_participant_id', '')
        parts = run_id_participant_id.rsplit('_', 1)
        
        if len(parts) < 2:
            return {"statusCode": 400, "body": json.dumps({"message": "Invalid ID format"})}
        
        run_id = parts[0]
        participant_id = parts[1]

        if not campaign_id:
            return {"statusCode": 401, "body": json.dumps({"status": "error", "message": "Invalid Token"})}

        with ThreadPoolExecutor() as executor:
            future_run = executor.submit(get_item, RUN_TABLE_NAME, {
                'campaign_id': campaign_id,
                'run_id': run_id
            })
            future_user = executor.submit(get_item, PARTICIPANT_TABLE_NAME, {
                'run_id': run_id,
                'participant_id': participant_id
            })
            
            run_item = future_run.result()
            user_item = future_user.result()
        if not run_item:
            return {"statusCode": 404, "body": json.dumps({"status": "error", "message": "活動不存在"})}

        deadline = run_item.get('registration_deadline')
        now = datetime.utcnow().isoformat()
        is_registration_closed = False
        if deadline:
            is_registration_closed = now > deadline

        if not user_item:
            return {"statusCode": 401, "body": json.dumps({"status": "error", "message": "Unauthorized: Participant not found"})}


        current_status = user_item.get('rsvp_status', 'PENDING')
        participant_name = user_item.get('name', token_name)

        response_body = {
            "status": "success",
            "data": {
                "current_status": current_status,
                "participant_name": participant_name,
                "run_info": {
                    "event_name": run_item.get('event_name', 'AWS Cloud Workshop'),
                    "event_time": run_item.get('event_time'),
                    "location": run_item.get('location'),
                    "registration_deadline": deadline,
                    "isRegistration_closed": is_registration_closed
                }
            }
        }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*" 
            },
            "body": json.dumps(response_body)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500, 
            "body": json.dumps({"status": "error", "message": "系統忙碌中"})
        }