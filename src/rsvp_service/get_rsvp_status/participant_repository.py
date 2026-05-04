import logging
import os

import boto3

logger = logging.getLogger()


class ParticipantRepository:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        table_name = os.environ.get("PARTICIPANT_TABLE")
        if not table_name:
            logger.error("PARTICIPANT_TABLE environment variable is not set")
            raise ValueError("PARTICIPANT_TABLE not set")

        self.table = self.dynamodb.Table(table_name)

    def get_participant(self, run_id, participant_id):
        try:
            response = self.table.get_item(
                Key={"run_id": run_id, "participant_id": participant_id}
            )
            return response.get("Item")
        except Exception as e:
            logger.error("Error fetching participant: %s", e)
            raise e
