import json
import logging

from dynamodb import DynamoDB
from ses import SES

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        code = event['queryStringParameters']['code']
        is_attend = event['queryStringParameters']['is_attend']
        logger.info(f"Received code: {code}, is_attend: {is_attend}")

        # * 先寫死
        # TODO 之後應該要換成從s3讀名單, 想辦法生成unique code
        dummy_participants = [
            {'code': '1', 'name': 'Richie', 'email': 'rich.liu627@gmail.com'},
            {'code': '2', 'name': 'Shiun', 'email': 'shiunchiu.me@gmail.com'},
            {'code': '3', 'name': 'Harry', 'email': 'harryup2000@gmail.com'}
        ]

        participant = next((p for p in dummy_participants if p['code'] == code), None)
        logger.info("Participant: %s", participant)

        if participant:
            # * 這邊就把display_name寫死
            send_confirmation_email("no-reply", participant['name'], participant['email'], is_attend)

            save_to_dynamodb(participant['name'], 'c14274978654c2488923d7fee1eb61f', participant['code'], participant['email'], is_attend)

            html_response = f"""
            <html>
            <head>
            <meta charset="UTF-8">
            </head>
            <body>
            <h1>登記出席成功</h1>
            <p>恭喜您成功登記出席，稍後會收到一封系統信件以表示系統已收到回應。</p>
            <p>若沒有收到該信件，務必聯繫我們：</p>
            <p>Facebook: <a href="https://bit.ly/3pD9aCr">台灣 AWS Educate Cloud Ambassador Facebook</a></p>
            <p>Instagram: <a href="https://bit.ly/3BBr7XQ">台灣 AWS Educate Cloud Ambassador Instagram</a></p>
            </body>
            </html>
            """
            status = "success"
            message = f"參與者 {participant['name']} 的出席狀態已更新為{is_attend}."

        response = {
            'statusCode': 200,
            'body': html_response,
            'headers': {
                'Content-Type': 'text/html'
            }
        }

        logger.info("Response: %s", response)
        return response

    except Exception as e:
        logger.error("Error in lambda_handler: %s", e, exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': "error",
                'message': f"Internal server error: {str(e)}"
            }),
            'headers': {
                'Content-Type': 'application/json'
            }
        }

def send_confirmation_email(display_name, name, email, is_attend):
    try:
        ses = SES()
        source_email = "awseducate.cloudambassador@gmail.com"
        formatted_source_email = f"{display_name} <{source_email}>"
        email_title = "出席確認"
        
        # 根據 is_attend 的值設定出席狀態文本
        attendance_status = "會出席" if is_attend == "true" else "不會出席"

        formatted_content = f"""
        <html>
        <head>
        <meta charset="UTF-8">
        </head>
        <body>
        <p>{name} 你好,</p>
        <p>您的出席狀態已更新為 {attendance_status}。感謝您的回應！</p>
        <p>若您未收到確認郵件，請聯繫我們：</p>
        <p>Facebook: <a href="https://bit.ly/3pD9aCr">台灣 AWS Educate Cloud Ambassador Facebook</a></p>
        <p>Instagram: <a href="https://bit.ly/3BBr7XQ">台灣 AWS Educate Cloud Ambassador Instagram</a></p>
        </body>
        </html>
        """
        ses.send_email(
            formatted_source_email=formatted_source_email,
            receiver_email=email,
            email_title=email_title,
            formatted_content=formatted_content
        )
        logger.info("Confirmation email sent to %s", email)

    except Exception as e:
        logger.error("Failed to send confirmation email to %s: %s", email, e)
        raise

def save_to_dynamodb(name, campaign_id, participant_id, email, is_attend):
    try:
        dynamodb = DynamoDB()
        item = {
            'campaign_id': campaign_id,
            'participant_id': participant_id,
            'name': name,
            'email': email,
            'is_attend':  is_attend
        }
        dynamodb.put_item('campaign', item)
        logger.info("Record saved to DynamoDB: %s", item)

    except Exception as e:
        logger.error("Failed to save record to DynamoDB: %s", e)
        raise