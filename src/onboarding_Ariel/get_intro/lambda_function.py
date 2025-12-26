import json

def lambda_handler(event, context):
    """AWS Lambda 處理器函式"""
    
    # 這是你要回傳的內容
    response_body = {
        "name": "Ariel",
        "introduction": "Hi! I'm Ariel, part of the 8th Tech cohort, and I will be joining the TPET team as a backend developer. I enjoy listening to K-pop and playing the piano. Looking forward to working with everyone!",
        "onboarding_path": "/onboarding_ariel"
    }

    # API Gateway 要求的回傳格式
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(response_body, ensure_ascii=False)
    }
