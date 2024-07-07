import json
import boto3
from s3 import S3
from ses import SES
from dynamodb import DynamoDB

def lambda_handler(event, context):
    code = event['queryStringParameters']['code']
    is_attend = event['queryStringParameters']['is_attend']
    
    # 模擬查詢參與者
    dummy_participants = [
        {'code': '1', 'name': 'Richie', 'email': 'rich.liu627@gmail.com'},
        {'code': '2', 'name': 'Shiun', 'email': 'shiunchiu.me@gmail.com'},
        {'code': '3', 'name': 'Harry', 'email': 'harryup2000@gmail.com'}
    ]

    participant = next((p for p in dummy_participants if p['code'] == code), None)

    if participant:
        # 更新出席狀態（這裡只是模擬）
        response_message = f"Participant {participant['name']} attendance status updated to {is_attend}"

        # 發送確認郵件
        send_confirmation_email(participant['name'], participant['email'], is_attend)

        # 將記錄保存到 DynamoDB
        save_to_dynamodb(participant['name'], participant['email'], is_attend)
    else:
        response_message = "Invalid code."

    return {
        'statusCode': 200,
        'body': json.dumps(response_message),
        'headers': {
            'Content-Type': 'text/html'
        }
    }

def send_confirmation_email(name, email, is_attend):
    ses_client = SES()
    formatted_source_email = "awseducate.cloudambassador@gmail.com"
    email_title = "Attendance Confirmation"
    formatted_content = f"""
    <html>
    <body>
    <h1>Attendance Confirmation</h1>
    <p>Dear {name},</p>
    <p>Your attendance status has been updated to {is_attend}. Thank you for your response!</p>
    <p>If you do not receive a confirmation email, please contact us via IG, FB, etc.</p>
    </body>
    </html>
    """
    ses_client.send_email(formatted_source_email, email, email_title, formatted_content)

def save_to_dynamodb(name, email, is_attend):
    dynamodb_client = DynamoDB()
    item = {
        'campaign_id': '1',                    
        'participant_id': name,
        'email': email,
        'is_attend': is_attend
    }
    dynamodb_client.put_item('campaign', item)