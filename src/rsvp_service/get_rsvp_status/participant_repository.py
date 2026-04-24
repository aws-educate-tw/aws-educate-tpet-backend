import boto3
import logging

logger = logging.getLogger()

class ParticipantRepository:
    def __init__(self, table_name):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)

    def get_participant(self, run_id, participant_id):
        try:
            response = self.table.get_item(Key={
                'run_id': run_id,
                'participant_id': participant_id
            })
            return response.get('Item')
        except Exception as e:
            logger.error(f"Error fetching participant: {str(e)}")
            raise e