import json
import logging
import os
from decimal import Decimal
from typing import Dict

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))
total_count_table = dynamodb.Table(os.getenv("DYNAMODB_TABLE_TOTAL_COUNT"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Convert Decimal to float or int, depending on your needs
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def get_total_count(webhook_type: str) -> int:
    """
    Get the total count of items for a specific webhook_type.
    """
    try:
        response = total_count_table.get_item(Key={"webhook_type": webhook_type})
        total_count = response.get("Item", {}).get("total_count", 0)
        return int(total_count)
    except Exception as e:
        logger.error(f"Error fetching total count for {webhook_type}: {str(e)}")
        raise

def lambda_handler(event: Dict, context) -> Dict:
    """
    Lambda function to fetch data from DynamoDB with optional limit, sort order, and pagination using sequence numbers.
    """
    query_params = event.get("queryStringParameters", {})
    limit = int(query_params.get("limit", 10))  # Default limit to 10
    sort_order = query_params.get("sort_order", "DESC").upper()  # Default to DESC
    page = int(query_params.get("page", 1))  # Default page number is 1
    webhook_type = query_params.get("webhook_type", "surveycake")  # Default webhook_type

    if not webhook_type:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': "'webhook_type' parameter is required."})
        }

    try:
        # Get total count from the total_count table
        total_count = get_total_count(webhook_type)

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

        # Query DynamoDB for the calculated range
        # The order of sequence_number is the same as the order of ascending order of created_at
        # So sorting by sequence_number is the same as sorting by created_at, we only need to use SequenceNumberIndex to sort here.
        response = table.query(
            IndexName="SequenceNumberIndex",
            KeyConditionExpression=Key("webhook_type").eq(webhook_type) &
                                   Key("sequence_number").between(start_key, end_key),
            ScanIndexForward=(sort_order == "ASC")  # True for ASC, False for DESC
        )
        data = response.get("Items", [])

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