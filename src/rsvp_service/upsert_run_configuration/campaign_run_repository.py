"""
Repository for upserting run configuration into the campaign_run DynamoDB table.
"""

import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CampaignRunRepository:
    """Repository for managing campaign run configurations in DynamoDB."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.environ["DYNAMODB_TABLE_RUN"])

    def upsert_run_configuration(
        self, campaign_id: str, run_id: str, config: dict
    ) -> None:
        """
        Insert or update a run configuration in the campaign_run table.

        Builds a DynamoDB UpdateItem expression from the provided config dict
        so the operation is idempotent — existing counters or fields not present
        in config are left untouched.

        :param campaign_id: Partition key.
        :param run_id: Sort key.
        :param config: Fields to set (must not contain campaign_id or run_id).
        :raises ClientError: Propagated so the caller can return a 500.
        """
        if not config:
            return

        set_expressions = []
        expression_attribute_names = {}
        expression_attribute_values = {}

        for idx, (key, value) in enumerate(config.items()):
            placeholder_name = f"#k{idx}"
            placeholder_value = f":v{idx}"
            set_expressions.append(f"{placeholder_name} = {placeholder_value}")
            expression_attribute_names[placeholder_name] = key
            expression_attribute_values[placeholder_value] = value

        update_expression = "SET " + ", ".join(set_expressions)

        try:
            self.table.update_item(
                Key={"campaign_id": campaign_id, "run_id": run_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
            )
            logger.info(
                "Upserted run configuration for campaign_id=%s run_id=%s",
                campaign_id,
                run_id,
            )
        except ClientError as e:
            logger.error(
                "Error upserting run configuration for campaign_id=%s run_id=%s: %s",
                campaign_id,
                run_id,
                e,
            )
            raise
