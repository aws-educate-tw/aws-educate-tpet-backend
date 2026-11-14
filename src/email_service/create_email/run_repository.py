import os

import boto3


class RunRepository:
    """Read and persist the schedule associated with a run."""

    def __init__(self):
        self._rds_data = boto3.client("rds-data")
        self._database_name = os.environ["DATABASE_NAME"]
        self._resource_arn = os.environ["RDS_CLUSTER_ARN"]
        self._secret_arn = os.environ["RDS_CLUSTER_MASTER_USER_SECRET_ARN"]

    def get_schedule_arn(self, run_id: str) -> str | None:
        response = self._execute(
            "SELECT schedule_arn FROM runs WHERE run_id = :run_id",
            [{"name": "run_id", "value": {"stringValue": run_id}}],
        )
        records = response.get("records", [])
        if not records:
            raise ValueError(f"Run not found: {run_id}")
        return records[0][0].get("stringValue")

    def update_schedule_arn(self, run_id: str, schedule_arn: str) -> None:
        response = self._execute(
            """
            UPDATE runs
            SET schedule_arn = :schedule_arn, updated_at = CURRENT_TIMESTAMP
            WHERE run_id = :run_id
            """,
            [
                {"name": "schedule_arn", "value": {"stringValue": schedule_arn}},
                {"name": "run_id", "value": {"stringValue": run_id}},
            ],
        )
        if response.get("numberOfRecordsUpdated") != 1:
            raise RuntimeError(f"Failed to save schedule ARN for run: {run_id}")

    def _execute(self, sql: str, parameters: list) -> dict:
        return self._rds_data.execute_statement(
            resourceArn=self._resource_arn,
            secretArn=self._secret_arn,
            database=self._database_name,
            sql=sql,
            parameters=parameters,
        )
