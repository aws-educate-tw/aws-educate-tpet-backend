import logging

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class SES:
    """
    SES operations
    """
    def __init__(self):
        self.ses_client = boto3.client(
            'ses'
        )

    def send_email(self, formatted_source_email: str, receiver_email: str, email_title: str, formatted_content: str):
        try:
            response = self.ses_client.send_email(
                Source=formatted_source_email,
                Destination={
                    "ToAddresses": [receiver_email]},
                Message={
                    "Subject": {"Data": email_title},
                    "Body": {"Html": {"Data": formatted_content}},
                },
            )
            return response
        except Exception as e:
            logger.error("Error sending email to %s: %s", receiver_email, e)
            raise