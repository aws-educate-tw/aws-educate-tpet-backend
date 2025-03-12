import logging

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class S3Util:
    def __init__(self, bucket_name: str):
        self.s3_client = boto3.client("s3")
        self.bucket_name = bucket_name

    def copy_file_to_run_folder(
        self, source_key: str, run_id: str, file_type: str, file_name: str | None = None
    ) -> str:
        """Copy file to runs/{run_id} folder

        :param source_key: Source file key in S3
        :param run_id: Run ID
        :param file_type: Type of file (template/spreadsheet/attachment)
        :param file_name: Optional custom file name
        """
        if file_name is None:
            file_name = source_key.split("/")[-1]

        new_key = f"runs/{run_id}/{file_type}/{file_name}"

        try:
            self.s3_client.copy_object(
                Bucket=self.bucket_name,
                CopySource={"Bucket": self.bucket_name, "Key": source_key},
                Key=new_key,
            )
            logger.info("Copied files from %s to %s", source_key, new_key)
            return new_key
        except Exception as e:
            logger.error("Error copying files to run folder: %s", e)
            raise
