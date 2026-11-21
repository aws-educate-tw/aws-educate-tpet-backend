import os

import boto3
import time_util
from run_status_enum import RunStatus


def _string_param(name: str, value: str) -> dict:
    return {"name": name, "value": {"stringValue": value}}


def _timestamp_param(name: str, iso8601_str: str) -> dict:
    """Same timestamp conversion as _create_param in the other repositories."""
    return {
        "name": name,
        "value": {
            "stringValue": time_util.format_datetime_for_rds(
                time_util.parse_iso8601_to_datetime(iso8601_str)
            )
        },
        "typeHint": "TIMESTAMP",
    }


class RunRepository:
    """Claim scheduled runs and keep their status in step with their emails."""

    def __init__(self):
        self._rds_data = boto3.client("rds-data")
        self._database_name = os.environ["DATABASE_NAME"]
        self._resource_arn = os.environ["RDS_CLUSTER_ARN"]
        self._secret_arn = os.environ["RDS_CLUSTER_MASTER_USER_SECRET_ARN"]

    def claim_scheduled_run(self, run_id: str) -> bool:
        """
        Move a SCHEDULED run to SENDING and record when it was dispatched.

        The status condition makes the claim atomic, so it can't succeed together
        with a cancel or send-now from update_run_schedule on the same run.

        :param run_id: The ID of the run to claim
        :return: True if the run was SCHEDULED and is now SENDING, False otherwise
        """
        now = time_util.get_current_utc_time()
        response = self._execute(
            """
            UPDATE runs
            SET status = :sending_status, dispatched_at = :dispatched_at
            WHERE run_id = :run_id AND status = :scheduled_status
            """,
            [
                _string_param("sending_status", RunStatus.SENDING.value),
                _timestamp_param("dispatched_at", now),
                _string_param("run_id", run_id),
                _string_param("scheduled_status", RunStatus.SCHEDULED.value),
            ],
        )
        return response.get("numberOfRecordsUpdated") == 1

    def get_run_status(self, run_id: str) -> str | None:
        """
        Get the current status of a run.

        :param run_id: The ID of the run
        :return: The status of the run, or None if the run doesn't exist
        """
        response = self._execute(
            "SELECT status FROM runs WHERE run_id = :run_id",
            [_string_param("run_id", run_id)],
        )
        records = response.get("records", [])
        if not records:
            return None
        return records[0][0].get("stringValue")

    def increment_failed_email_count(self, run_id: str) -> None:
        """
        Increment the failed_email_count for a run.

        :param run_id: The run ID to update
        """
        self._execute(
            """
            UPDATE runs
            SET failed_email_count = failed_email_count + 1
            WHERE run_id = :run_id
            """,
            [_string_param("run_id", run_id)],
        )

    def finalize_run_status_if_complete(self, run_id: str) -> None:
        """
        Set a SENDING run to SENT, or FAILED if any email failed, once the
        success and failed counts reach expected_email_send_count.

        This is the same update send_email runs after every email. Runs in any
        other status are left untouched, so it is safe to call more than once.

        :param run_id: The run ID to update
        """
        self._execute(
            """
            UPDATE runs
            SET status = CASE WHEN failed_email_count > 0 THEN :failed_status ELSE :sent_status END
            WHERE run_id = :run_id
              AND status = :sending_status
              AND success_email_count + failed_email_count >= expected_email_send_count
            """,
            [
                _string_param("run_id", run_id),
                _string_param("sending_status", RunStatus.SENDING.value),
                _string_param("sent_status", RunStatus.SENT.value),
                _string_param("failed_status", RunStatus.FAILED.value),
            ],
        )

    def _execute(self, sql: str, parameters: list) -> dict:
        return self._rds_data.execute_statement(
            resourceArn=self._resource_arn,
            secretArn=self._secret_arn,
            database=self._database_name,
            sql=sql,
            parameters=parameters,
        )
