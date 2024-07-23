import logging

import jwt

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda function to handle GET /auth/is-logged-in API request.

    This function reads the accessToken from cookies, decodes the JWT to check if the token is valid.

    Parameters:
    event (dict): API Gateway Lambda Proxy Input Format
    context (LambdaContext): Lambda Context runtime methods and attributes

    Returns:
    dict: API Gateway Lambda Proxy Output Format
    """

    # Get accessToken from cookies
    cookies = event.get("headers", {}).get("Cookie", "")
    access_token = None
    for cookie in cookies.split(";"):
        if "accessToken=" in cookie:
            access_token = cookie.split("=")[1]
            break

    if not access_token:
        return {
            "statusCode": 200,
            "body": "false",
            "headers": {"Content-Type": "application/json"},
        }

    try:
        # Decode JWT to check validity
        decoded_token = jwt.decode(access_token, options={"verify_signature": False})
        user_id = decoded_token.get("sub")

        if not user_id:
            return {
                "statusCode": 200,
                "body": "false",
                "headers": {"Content-Type": "application/json"},
            }

        return {
            "statusCode": 200,
            "body": "true",
            "headers": {"Content-Type": "application/json"},
        }

    except jwt.ExpiredSignatureError:
        return {
            "statusCode": 200,
            "body": "false",
            "headers": {"Content-Type": "application/json"},
        }

    except jwt.InvalidTokenError:
        return {
            "statusCode": 200,
            "body": "false",
            "headers": {"Content-Type": "application/json"},
        }
