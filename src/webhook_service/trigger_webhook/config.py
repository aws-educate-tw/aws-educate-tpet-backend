import os


class Config:
    DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE")
    ENVIRONMENT = os.getenv("ENVIRONMENT")
    SEND_EMAIL_API_ENDPOINT = os.getenv("SEND_EMAIL_API_ENDPOINT")
    SERVICE_ACCOUNTS = ["surveycake"]