import json
import logging
import os
from decimal import Decimal

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")

CAMPAIGNS_TABLE = os.getenv("CAMPAIGNS_TABLE", "campaign")


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects."""

    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def _response(status_code, body):
    """Build a standardized API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def _scan_all_campaigns(campaigns_table):
    """Scan all campaigns from DynamoDB with pagination."""
    items = []
    scan_kwargs = {}

    while True:
        response = campaigns_table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

    return items


def _format_campaign(campaign_item):
    """Format campaign item for API response."""
    return {
        "campaign_id": campaign_item.get("campaign_id"),
        "campaign_name": campaign_item.get("campaign_name"),
        "campaign_start_time": campaign_item.get("campaign_start_time"),
        "campaign_end_time": campaign_item.get("campaign_end_time"),
        "campaign_location": campaign_item.get("campaign_location"),
        "campaign_created_at": campaign_item.get("created_at"),
        "is_active": bool(campaign_item.get("is_active")),
    }


def _safe_event_log_fields(event):
    """Extract non-sensitive event metadata for logging."""
    request_context = event.get("requestContext") or {}
    http_context = request_context.get("http") or {}

    return {
        "action": event.get("action"),
        "path": event.get("path") or http_context.get("path"),
        "httpMethod": event.get("httpMethod") or http_context.get("method"),
        "requestId": request_context.get("requestId"),
    }


def lambda_handler(event: dict[str, any], context: object) -> dict[str, any]:
    """Lambda function handler for listing all campaign summaries."""
    aws_request_id = getattr(context, "aws_request_id", None)
    logger.info("Received event metadata: %s", _safe_event_log_fields(event))

    if event.get("action") == "PREWARM":
        logger.info(
            "Received a prewarm request. Skipping business logic. Request ID: %s",
            aws_request_id,
        )
        return {"statusCode": 200, "body": "Successfully warmed up"}

    campaigns_table = dynamodb.Table(CAMPAIGNS_TABLE)

    try:
        campaign_items = _scan_all_campaigns(campaigns_table)
        response_body = [_format_campaign(item) for item in campaign_items]
        return _response(200, response_body)

    except (ClientError, BotoCoreError) as error:
        logger.exception("Database error when listing campaigns: %s", error)
        return _response(
            500,
            {
                "message": "Failed to query campaign data.",
            },
        )
