"""
This lambda function triggers a webhook by processing 
the incoming request from the surveycake webhook.
"""
import json
import logging

from webhook_handler import WebhookHandler
from webhook_repository import WebhookRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

webhook_handler = WebhookHandler()
webhook_repository = WebhookRepository()

def lambda_handler(event, context): # pylint: disable=unused-argument
    """ Lambda function handler to trigger the webhook """

    # Identify if the incoming event is a prewarm request
    if event.get("action") == "PREWARM":
        logger.info("Received a prewarm request. Skipping business logic.")
        return {"statusCode": 200, "body": "Successfully warmed up"}

    try:
        header = event.get("headers", {})

        # Check if the User-Agent is allowed
        check_headers_agent = webhook_handler.check_headers_agent(header)
        if not check_headers_agent:
            return {
                "statusCode": 403,
                "body": json.dumps({"message": "Forbidden: Unauthorized User-Agent"}),
            }
        
        # Get the webhook details from the DynamoDB using the webhook_id
        webhook_id = event["pathParameters"]["webhook_id"]
        webhook_details = webhook_repository.get_webhook_details(webhook_id)
        logger.info("Webhook details in DynamoDB: %s", webhook_details)

        if not webhook_details:
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "Webhook not found"}),
            }

        try:
            # Process the request body to get the svid and hash values
            svid_value, hash_value = webhook_handler.process_request_body(
                event.get("body"), event.get("isBase64Encoded", False)
            )
            logger.info("Decoded svid: %s, hash: %s", svid_value, hash_value)

            # Get the surveycake data using the svid and hash values
            encrypted_data = webhook_handler.get_surveycake_data(svid_value, hash_value)

        except ValueError as e:
            return {"statusCode": 400, "body": json.dumps({"error": str(e)})}

        try:
            # Decrypt the surveycake data using the hash and iv keys
            # hash_key and iv_key are stored in fetched dynamodb
            decrypted_str = webhook_handler.crypto_handler.decrypt_data(
                encrypted_data, webhook_details["hash_key"], webhook_details["iv_key"]
            )

        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"Failed to decrypt data: {str(e)}"}),
            }

        # Parse the decrypted data to get the recipient email
        answer_data = json.loads(decrypted_str)
        logger.info("All the decrypted data from surveycake: %s", answer_data)
        recipient_email = webhook_handler.extract_recipient_email(answer_data)
        logger.info("Recipient email extracted from surveycake: %s", recipient_email)

        if not recipient_email:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No email found in the surveycake data"}),
            }

        # Prepare the email body to send the email
        email_body = webhook_handler.prepare_email_body(webhook_details, recipient_email)
        email_status = webhook_handler.send_email(email_body)
        logger.info("Email status: %s", email_status)

        if email_status.get("statusCode") != 202:
            return {
                "statusCode": email_status.get("statusCode", 500),
                "body": json.dumps(
                    {
                        "status": "error",
                        "message": "Failed to send email",
                        "details": email_status.get("body"),
                    }
                ),
            }

        # Successful response
        return {
            "statusCode": 202,
            "body": json.dumps(
                {
                    "status": "success",
                    "message": "Email is being processed successfully",
                    "data": {
                        "recipient_email": recipient_email,
                        "webhook_id": webhook_id,
                    },
                    "send_email_response": {
                        "status_code": email_status.get("statusCode"),
                        "body": email_status.get("body"),
                    },
                }
            ),
        }

    except Exception as e:
        logger.error("Error: %s", str(e))
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
