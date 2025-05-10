import json
import os

import boto3

# Initialize the RDS Data Service client
rds_data = boto3.client("rds-data")

DATABASE_NAME = os.environ["DATABASE_NAME"]
CLUSTER_ARN = os.environ["CLUSTER_ARN"]
SECRET_ARN = os.environ["SECRET_ARN"]

# List of columns known to be JSONB
jsonb_columns = {
    "attachment_file_ids",
    "attachment_files",
    "bcc",
    "cc",
    "recipients",
    "sender",
    "spreadsheet_file",
    "template_file"
}

def parse_field(col_name, field):
    if "isNull" in field and field["isNull"]:
        return None
    if "stringValue" in field:
        value = field["stringValue"]
        # Try parsing JSONB fields
        if col_name in jsonb_columns:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value  # fallback to raw string if not valid JSON
        return value
    if "longValue" in field:
        return field["longValue"]
    if "booleanValue" in field:
        return field["booleanValue"]
    if "doubleValue" in field:
        return field["doubleValue"]
    if "arrayValue" in field:
        return field["arrayValue"]
    if "blobValue" in field:
        return field["blobValue"]
    return field  # fallback for unknown types

def lambda_handler(event, context):
    sql_statement = """
        SELECT
            run_id,
            run_type,
            attachment_file_ids,
            attachment_files,
            bcc,
            cc,
            created_at,
            created_year,
            created_year_month,
            created_year_month_day,
            display_name,
            expected_email_send_count,
            is_generate_certificate,
            recipients,
            reply_to,
            sender,
            sender_id,
            sender_local_part,
            spreadsheet_file,
            spreadsheet_file_id,
            subject,
            success_email_count,
            template_file,
            template_file_id
        FROM RUNS
        ORDER BY created_at DESC
    """

    try:
        response = rds_data.execute_statement(
            resourceArn=CLUSTER_ARN,
            secretArn=SECRET_ARN,
            database=DATABASE_NAME,
            sql=sql_statement
        )
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

    columns = [
        "run_id",
        "run_type",
        "attachment_file_ids",
        "attachment_files",
        "bcc",
        "cc",
        "created_at",
        "created_year",
        "created_year_month",
        "created_year_month_day",
        "display_name",
        "expected_email_send_count",
        "is_generate_certificate",
        "recipients",
        "reply_to",
        "sender",
        "sender_id",
        "sender_local_part",
        "spreadsheet_file",
        "spreadsheet_file_id",
        "subject",
        "success_email_count",
        "template_file",
        "template_file_id",
    ]

    runs = []
    for record in response["records"]:
        row = {
            col_name: parse_field(col_name, field)
            for col_name, field in zip(columns, record)
        }
        runs.append(row)

    return {
        "statusCode": 200,
        "body": json.dumps({"runs": runs, "message": "The runs have been fetched successfully."}, indent=2, default=str)
    }