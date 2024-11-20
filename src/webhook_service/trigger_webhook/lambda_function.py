import json
import os
from decimal import Decimal
import requests
import boto3
import base64
from urllib.parse import parse_qs
from Crypto.Cipher import AES

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


def lambda_handler(event, context):
    # Retrieve the webhook details from the dynamoDB
    webhook_id = event["pathParameters"]["webhook_id"]
    webhook_details = table.get_item(Key={"webhook_id": webhook_id})

    if "Item" not in webhook_details:
        return {
            "statusCode": 404, 
            "body": json.dumps({"message": "Webhook not found"})
        }

    webhook_details_item = webhook_details.get("Item")

    if webhook_details_item is None:
        return {
            "statusCode": 404, 
            "body": json.dumps({"message": "No webhook details found"})
        }


    # Extract and decode the body
    surveycake_data = event.get('body')
    if surveycake_data is None:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No body in the request'})
        }

    if event.get('isBase64Encoded', False):
        decoded_bytes = base64.b64decode(surveycake_data)
        decoded_str = decoded_bytes.decode('utf-8')
    else:
        decoded_str = surveycake_data

    # Parse query parameters from the decoded string
    params = parse_qs(decoded_str)
    svid_value = params.get('svid', [None])[0]
    hash_value = params.get('hash', [None])[0]

    if not svid_value or not hash_value:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing svid or hash in the request'})
        }
    
    # Construct the API URL and retrieve the encrypted data
    api_url = f'https://www.surveycake.com/webhook/v0/{svid_value}/{hash_value}'
    encrypted_data_response = requests.get(api_url)

    # Ensure the request was successful
    if encrypted_data_response.status_code != 200:
        return {
            'statusCode': encrypted_data_response.status_code,
            'body': json.dumps({'error': 'Failed to retrieve data from the API'})
        }
    
    encrypted_data = base64.b64decode(encrypted_data_response.content)
    print("encrypted_data", encrypted_data)

    # Retrieve hash_key and IV_key from the DynamoDB item
    hash_key = webhook_details_item.get('hash_key').encode('utf-8')
    iv_key = webhook_details_item.get('IV_key').encode('utf-8')

    try:
        cipher = AES.new(hash_key, AES.MODE_CBC, iv_key)
        decrypted_data = cipher.decrypt(encrypted_data).rstrip(b'\0')
        decrypted_str = decrypted_data.decode('utf-8')
        print("decrypted_str", decrypted_str)

        last_brace_index = decrypted_str.rfind('}')
        if last_brace_index != -1:
            cleaned_decrypted_str = decrypted_data[:last_brace_index + 1]
        else:
            raise ValueError('Invalid JSON data')
        
        answer_data = json.loads(cleaned_decrypted_str)
        print("answer_data", answer_data)

        # Extract the email from the '你的信箱' field
        recipient_email = None
        for i in answer_data['result']:
            if i['subject'] == '你的信箱':
                recipient_email = i['answer'][0]
                print("Recipient email found:", recipient_email)
                break
        
        if recipient_email : 
            recipients = [
                {
                    "email": recipient_email,
                    "template_variables": {}
                }
            ]
            send_email_body = {
                "recipient_source": "DIRECT",
                "subject": webhook_details_item["subject"],
                "display_name": webhook_details_item["display_name"],
                "template_file_id": webhook_details_item["template_file_id"],
                "attachment_file_ids": webhook_details_item["attachment_file_ids"],
                "is_generate_certificate": webhook_details_item["is_generate_certificate"],
                "reply_to": webhook_details_item["reply_to"],
                "sender_local_part": webhook_details_item["sender_local_part"],
                "bcc": webhook_details_item["bcc"],
                "cc": webhook_details_item["cc"],
                "recipients": recipients,
                # "surveycake_link": webhook_details_item["surveycake_link"],
                # "hask_key": webhook_details_item["hask_key"],
                # "iv_key": webhook_details_item["iv_key"],
                # "webhook_name": webhook_details_item["webhook_name"]
            }
        
            send_email_status = send_email(send_email_body)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Email sent successfully',
                    'send_email_status': send_email_status
                })
            }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No email found for 你的信箱'})
            }

    except Exception as e:
        print(f'Failed to decrypt data: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to decrypt data: {str(e)}'})
        }

def send_email(send_email_body):
    try:
        send_email_api_endpoint = os.getenv('SEND_EMAIL_API_ENDPOINT')
        response = requests.post(
            send_email_api_endpoint,
            headers={
                'Content-Type': 'application/json',
            },
            body= json.dumps(send_email_body)
        )

        return response
    

    except Exception as e:
        print(f'Failed to send email: {str(e)}')
        return str(e)