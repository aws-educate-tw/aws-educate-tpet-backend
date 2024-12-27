import json
import logging
import os
from decimal import Decimal
from typing import Dict

import boto3
from webhook_repository import WebhookRepository
from webhook_total_count_repository import WebhookTotalCountRepository
from webhook_type_enum import WebhookType

WebhookRepository = WebhookRepository()
WebhookTotalCountRepository = WebhookTotalCountRepository()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            # Convert Decimal to float or int, depending on your needs
            return float(o)
        return super(DecimalEncoder, self).default(o)


def lambda_handler(event: Dict, context) -> Dict:
    """
    Lambda function to fetch data from DynamoDB with optional limit, sort order, and pagination using sequence numbers.
    """
    query_params = event.get("queryStringParameters", {})
    limit = int(query_params.get("limit", 10))  # Default limit to 10
    sort_order = query_params.get("sort_order", "DESC").upper()  # Default to DESC
    page = int(query_params.get("page", 1))  # Default page number is 1
    webhook_type = query_params.get("webhook_type") # Required parameter

    if not webhook_type or webhook_type.strip() == "":
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': "'webhook_type' parameter is required and cannot be empty."})
        }
    
    try:
        # Convert string webhook_type to Enum
        webhook_type_enum = WebhookType(webhook_type.lower())

    except ValueError:
        # Handle invalid webhook_type values
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f"Invalid webhook_type value: {webhook_type}. Must be one of {[e.value for e in WebhookType]}."})
        }

    try:
        # Get total count from the total_count table
        total_count = WebhookTotalCountRepository.get_total_count(webhook_type_enum.name)

        # Validate page number
        if page < 1:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Invalid page number."}),
            }
        
        elif limit < 1:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Invalid limit value."}),
            }
        
        
        elif (page - 1) * limit >= total_count:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Page number out of range."}),
            }

        # Calculate start and end range for the page
        if sort_order == "ASC":
            start_key = (page - 1) * limit + 1
            end_key = min(page * limit, total_count)
        else:  # DESC
            start_key = max(total_count - (page * limit) + 1, 1)
            end_key = total_count - (page - 1) * limit

        data = WebhookRepository.get_data(webhook_type, limit, sort_order, page, start_key, end_key)    

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "data": data,
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "sort_order": sort_order,
            }, cls=DecimalEncoder),  # Use the custom encoder here
        }
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Internal server error.",
                "message": str(e),
            }),
        }