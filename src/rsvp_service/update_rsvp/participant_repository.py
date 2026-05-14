import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()


class ParticipantRepository:
    def __init__(self):
        region = os.environ.get("AWS_REGION", "us-west-2")
        self.dynamodb = boto3.client("dynamodb", region_name=region)
        self.table_name = os.environ.get("PARTICIPANT_TABLE", "participant")

    def update_rsvp_transaction(self, transact_items):
        try:
            return self.dynamodb.transact_write_items(TransactItems=transact_items)
        except ClientError as e:
            logger.error("Transaction failed: %s", e)
            raise
