import json
import base64
import requests
from urllib.parse import parse_qs
from config import Config
from utils import DecimalEncoder, SecretsManager, CryptoHandler
from typing import Dict, Any, Optional, Tuple
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class WebhookHandler:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(Config.DYNAMODB_TABLE)
        self.secrets_manager = SecretsManager()
        self.crypto_handler = CryptoHandler()

    def get_webhook_details(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        webhook_details = self.table.get_item(Key={"webhook_id": webhook_id})
        return webhook_details.get("Item")

    def process_request_body(self, body: str, is_base64_encoded: bool) -> Tuple[str, str]:
        if body is None:
            raise ValueError('No body in the request')
            
        decoded_str = base64.b64decode(body).decode('utf-8') if is_base64_encoded else body
        params = parse_qs(decoded_str)
        
        svid_value = params.get('svid', [None])[0]
        hash_value = params.get('hash', [None])[0]
        
        if not svid_value or not hash_value:
            raise ValueError('Missing svid or hash in the request')
            
        return svid_value, hash_value

    def get_survey_data(self, svid: str, hash_value: str) -> bytes:
        api_url = f'https://www.surveycake.com/webhook/v0/{svid}/{hash_value}'
        response = requests.get(api_url)
        
        if response.status_code != 200:
            raise ValueError('Failed to retrieve data from the API')
            
        return base64.b64decode(response.content)

    def extract_recipient_email(self, answer_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the email address from the surveycake.
        CAUTION: There should be a question named "你的信箱" in one of the surveycake questions.
        """
        for item in answer_data['result']:
            if item['subject'] == '你的信箱':
                return item['answer'][0]
        return None

    def send_email(self, email_body: Dict[str, Any]) -> Dict[str, Any]:
        try:
            access_token = self.secrets_manager.get_access_token("surveycake")
            
            response = requests.post(
                Config.SEND_EMAIL_API_ENDPOINT,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {access_token}'
                },
                json=email_body
            )
            
            return {
                'statusCode': response.status_code,
                'body': response.json() if response.status_code == 200 else response.text
            }
        except Exception as e:
            print(f'Failed to send email: {str(e)}')
            return {'error': str(e)}

    def prepare_email_body(self, webhook_details: Dict[str, Any], recipient_email: str) -> Dict[str, Any]:
        return {
            "recipient_source": "DIRECT",
            "subject": webhook_details["subject"],
            "display_name": webhook_details["display_name"],
            "template_file_id": webhook_details["template_file_id"],
            "attachment_file_ids": webhook_details["attachment_file_ids"],
            "is_generate_certificate": webhook_details["is_generate_certificate"],
            "reply_to": webhook_details["reply_to"],
            "sender_local_part": webhook_details["sender_local_part"],
            "bcc": webhook_details["bcc"],
            "cc": webhook_details["cc"],
            "recipients": [
                {
                    "email": recipient_email,
                    "template_variables": {}
                }
            ]
        }

def lambda_handler(event, context):
    try:
        handler = WebhookHandler()
        webhook_id = event["pathParameters"]["webhook_id"]
        webhook_details = handler.get_webhook_details(webhook_id)
        logger.info(f'Webhook details that have been saved to DynamoDB: {webhook_details}')
        
        if not webhook_details:
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "Webhook not found"})
            }
        
        try:
            svid_value, hash_value = handler.process_request_body(
                event.get('body'),
                event.get('isBase64Encoded', False)
            )
        except ValueError as e:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': str(e)})
            }
        
        try:
            encrypted_data = handler.get_survey_data(svid_value, hash_value)
        except ValueError as e:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': str(e)})
            }
        
        try:
            decrypted_str = handler.crypto_handler.decrypt_data(
                encrypted_data,
                webhook_details['hash_key'],
                webhook_details['iv_key']
            )
        except Exception as e:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': f'Failed to decrypt data: {str(e)}'})
            }
        
        answer_data = json.loads(decrypted_str)
        logger.info(f'All the decrypted data from surveycake: {answer_data}')
        recipient_email = handler.extract_recipient_email(answer_data)
        logger.info(f'Recipient email extracted from surveycake: {recipient_email}')
        
        if not recipient_email:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No email found for 你的信箱'})
            }
        
        email_body = handler.prepare_email_body(webhook_details, recipient_email)
        send_email_status = handler.send_email(email_body)
        logger.info(f'Email sent successfully: {send_email_status}')
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Email sent successfully',
                'send_email_status': send_email_status
            })
        }
        
    except Exception as e:
        print(f'Error processing webhook: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }