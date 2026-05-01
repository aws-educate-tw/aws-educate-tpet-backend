import logging
import boto3

logger = logging.getLogger()

class CampaignRunRepository:
    def __init__(self, table_name):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def get_run(self, campaign_id, run_id):
        try:
            response = self.table.get_item(
                Key={"campaign_id": campaign_id, "run_id": run_id}
            )
            return response.get("Item")
        except Exception as e:
            logger.error("Error fetching run from campaign_run_repository: %s", e)
            raise e