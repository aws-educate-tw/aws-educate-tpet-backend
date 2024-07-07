import logging
import os

import boto3
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class S3:
    """
    S3 operations
    """
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            region_name=os.getenv('REGION_NAME')
        )

    def create_bucket(self, bucket_name: str):
        """
        Create an S3 bucket
        """
        try:
            self.s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': os.getenv('REGION_NAME')}
            )
            logger.info(f"Bucket {bucket_name} created successfully.")
        except Exception as e:
            logger.error(f"Error creating bucket {bucket_name}: {e}")

    def upload_file(self, file_name: str, bucket_name: str, object_name: str = None):
        """
        Upload a file to an S3 bucket
        """
        if object_name is None:
            object_name = file_name

        try:
            self.s3_client.upload_file(file_name, bucket_name, object_name)
            logger.info(f"File {file_name} uploaded to {bucket_name}/{object_name} successfully.")
        except Exception as e:
            logger.error(f"Error uploading file {file_name} to {bucket_name}/{object_name}: {e}")

    def list_files(self, bucket_name: str):
        """
        List files in an S3 bucket
        """
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket_name)
            if 'Contents' in response:
                for obj in response['Contents']:
                    logger.info(f"Found file: {obj['Key']}")
            else:
                logger.info(f"No files found in bucket {bucket_name}.")
        except Exception as e:
            logger.error(f"Error listing files in bucket {bucket_name}: {e}")

    def download_file(self, bucket_name: str, file_key: str, local_file_path: str):
        """
        Download a single file from an S3 bucket to a local path
        """
        try:
            self.s3_client.download_file(bucket_name, file_key, local_file_path)
            logger.info(f"Downloaded {file_key} to {local_file_path}")
        except Exception as e:
            logger.error(f"Error downloading file {file_key} from bucket {bucket_name}: {e}")

    def list_files(self, bucket_name: str):
        """
        List all files in an S3 bucket
        """
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket_name)
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            else:
                logger.info(f"No files found in bucket {bucket_name}.")
                return []
        except Exception as e:
            logger.error(f"Error listing files in bucket {bucket_name}: {e}")
            return []

    def get_object(self, bucket_name: str, key: str):
        """
        Get object from an S3 bucket
        """
        try:
            response = self.s3_client.get_object(Bucket=bucket_name, Key=key)
            return response
        except Exception as e:
            logger.error(f"Error getting object from bucket {bucket_name}: {e}")
            raise