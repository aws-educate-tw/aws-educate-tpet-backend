import io
import logging
import os

import boto3
import pandas as pd

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BUCKET_NAME = os.getenv("BUCKET_NAME")


def get_template(template_file_s3_key):
    try:
        s3 = boto3.client("s3")
        request = s3.get_object(Bucket=BUCKET_NAME, Key=template_file_s3_key)
        template_content = request["Body"].read().decode("utf-8")
        logger.info("Fetched template content from S3 key: %s", template_file_s3_key)
        return template_content
    except Exception as e:
        logger.error("Error in get_template: %s", e)
        raise


def read_sheet_data_from_s3(spreadsheet_file_s3_key):
    try:
        s3 = boto3.client("s3")
        request = s3.get_object(Bucket=BUCKET_NAME, Key=spreadsheet_file_s3_key)
        xlsx_content = request["Body"].read()
        excel_data = pd.read_excel(io.BytesIO(xlsx_content), engine="openpyxl")
        rows = excel_data.to_dict(orient="records")
        if excel_data.empty:
            return [], 0
        logger.info("Read sheet data from S3 key: %s", spreadsheet_file_s3_key)
        return rows, excel_data.columns.tolist()
    except Exception as e:
        logger.error("Error in read excel from s3: %s", e)
        raise


def read_file_from_s3(bucket_name, s3_key):
    """
    Read the content of a file from S3 bucket.

    :param bucket_name: The name of the S3 bucket.
    :param s3_key: The key (path) of the file in the S3 bucket.
    :return: The content of the file as bytes.
    """
    try:
        s3 = boto3.client("s3")
        response = s3.get_object(Bucket=bucket_name, Key=s3_key)
        file_content = response["Body"].read()
        logger.info("Successfully read file from S3: %s", s3_key)
        return file_content
    except Exception as e:
        logger.error("Error reading file from S3: %s", e)
        raise


def upload_file_to_s3(file_path, bucket_name, s3_key):
    s3 = boto3.client("s3")
    s3.upload_file(file_path, bucket_name, s3_key)
