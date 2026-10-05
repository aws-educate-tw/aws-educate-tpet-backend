import os

from aws_lambda_powertools.utilities.parameters import get_secret


def get_slack_config():
    secret_arn = os.environ["SLACK_ALERT_CONFIG_SECRET_ARN"]
    return get_secret(secret_arn, transform="json")
