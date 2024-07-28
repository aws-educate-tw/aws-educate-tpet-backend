import logging

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class S3:
    """
    S3 operations
    """
    def __init__(self):
        self.s3_client = boto3.client(
            's3'
        )

    def create_bucket(self, bucket_name: str):
        """
        Create an S3 bucket
        """
        try:
            self.s3_client.create_bucket(
                Bucket=bucket_name
            )
            logger.info("Bucket %s created successfully.", bucket_name)
        except Exception as e:
            logger.error("Error creating bucket %s: %s", bucket_name, e)

    def upload_file(self, file_name: str, bucket_name: str, object_name: str = None):
        """
        Upload a file to an S3 bucket
        """
        if object_name is None:
            object_name = file_name

        try:
            self.s3_client.upload_file(file_name, bucket_name, object_name)
            logger.info("File %s uploaded to %s/%s.", file_name, bucket_name, object_name)
        except Exception as e:
            logger.error("Error uploading file %s to bucket %s: %s", file_name, bucket_name, e)

    def list_files(self, bucket_name: str):
        """
        List files in an S3 bucket
        """
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket_name)
            if 'Contents' in response:
                for obj in response['Contents']:
                    logger.info("File found: %s", obj['Key'])
            else:
                logger.info("No files found in bucket %s.", bucket_name)
        except Exception as e:
            logger.error("Error listing files in bucket %s: %s", bucket_name, e)

    def download_file(self, bucket_name: str, file_key: str, local_file_path: str):
        """
        Download a single file from an S3 bucket to a local path
        """
        try:
            self.s3_client.download_file(bucket_name, file_key, local_file_path)
            logger.info("Downloaded file %s from bucket %s to %s.", file_key, bucket_name, local_file_path)
        except Exception as e:
            logger.error("Error downloading file %s from bucket %s: %s", file_key, bucket_name, e)

    def get_object(self, bucket_name: str, key: str):
        """
        Get object from an S3 bucket
        """
        try:
            response = self.s3_client.get_object(Bucket=bucket_name, Key=key)
            return response
        except Exception as e:
            logger.error("Error getting object %s from bucket %s: %s", key, bucket_name, e)
            raise