import json
import os

import boto3
import time_util
from email_status_enum import EmailStatus

JSONB_COLUMNS = {"attachment_file_ids", "bcc", "cc", "row_data"}


def parse_field(col_name: str, field: dict):
    """
    Parse a field value returned by RDS Data API.

    :param col_name: Column name
    :param field: Field value returned by RDS Data API
    :return: Converted Python value
    """
    if field.get("isNull"):
        return None
    if "stringValue" in field:
        value = field["stringValue"]
        return json.loads(value) if col_name in JSONB_COLUMNS else value
    if "booleanValue" in field:
        return field["booleanValue"]
    if "longValue" in field:
        return field["longValue"]
    return field


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


class EmailRepository:
    """Read the SCHEDULED emails of a run and update them once dispatched."""

    def __init__(self):
        self._rds_data = boto3.client("rds-data")
        self._database_name = os.environ["DATABASE_NAME"]
        self._resource_arn = os.environ["RDS_CLUSTER_ARN"]
        self._secret_arn = os.environ["RDS_CLUSTER_MASTER_USER_SECRET_ARN"]

    def list_scheduled_emails(self, run_id: str, limit: int, offset: int) -> list[dict]:
        """
        Get one page of the SCHEDULED emails of a run, oldest first, with the
        fields send_email reads from its SQS message.

        :param run_id: The ID of the run
        :param limit: Maximum number of emails to return
        :param offset: Number of emails to skip
        :return: List of emails
        """
        # email_id is a secondary, unique sort key to keep pagination stable
        response = self._execute(
            """
            SELECT email_id, recipient_email, subject, display_name, template_file_id,
                   row_data, attachment_file_ids, is_generate_certificate, sender_id,
                   reply_to, sender_local_part, cc, bcc
            FROM emails
            WHERE run_id = :run_id AND status = :scheduled_status
            ORDER BY created_at, email_id
            LIMIT :limit OFFSET :offset
            """,
            [
                _string_param("run_id", run_id),
                _string_param("scheduled_status", EmailStatus.SCHEDULED.value),
                {"name": "limit", "value": {"longValue": limit}},
                {"name": "offset", "value": {"longValue": offset}},
            ],
            include_result_metadata=True,
        )
        records = response.get("records", [])
        if not records:
            return []

        columns = [column["name"] for column in response["columnMetadata"]]
        return [
            {
                col: parse_field(col, val)
                for col, val in zip(columns, record, strict=True)
            }
            for record in records
        ]

    def mark_scheduled_email_pending(self, run_id: str, email_id: str) -> bool:
        """
        Mark a SCHEDULED email PENDING once it is in the send email queue.

        sent_at is left for send_email to set, like the PENDING emails saved by
        create_email. send_email can finish the email before this update runs,
        so the status condition keeps PENDING from overwriting its result.

        :param run_id: The ID of the run
        :param email_id: The ID of the email
        :return: True if the email was SCHEDULED and got updated, False otherwise
        """
        now = time_util.get_current_utc_time()
        response = self._execute(
            """
            UPDATE emails
            SET status = :status, updated_at = :updated_at
            WHERE run_id = :run_id AND email_id = :email_id AND status = :scheduled_status
            """,
            [
                _string_param("status", EmailStatus.PENDING.value),
                _timestamp_param("updated_at", now),
                _string_param("run_id", run_id),
                _string_param("email_id", email_id),
                _string_param("scheduled_status", EmailStatus.SCHEDULED.value),
            ],
        )
        return response.get("numberOfRecordsUpdated") == 1

    def mark_scheduled_email_failed(self, run_id: str, email_id: str) -> bool:
        """
        Mark a SCHEDULED email FAILED when it can't be put in the send email queue.

        sent_at is set too, as update_email_status does in the other Lambdas,
        so these emails match the other FAILED emails.

        :param run_id: The ID of the run
        :param email_id: The ID of the email
        :return: True if the email was SCHEDULED and got updated, False otherwise
        """
        now = time_util.get_current_utc_time()
        response = self._execute(
            """
            UPDATE emails
            SET status = :status, sent_at = :sent_at, updated_at = :updated_at
            WHERE run_id = :run_id AND email_id = :email_id AND status = :scheduled_status
            """,
            [
                _string_param("status", EmailStatus.FAILED.value),
                _timestamp_param("sent_at", now),
                _timestamp_param("updated_at", now),
                _string_param("run_id", run_id),
                _string_param("email_id", email_id),
                _string_param("scheduled_status", EmailStatus.SCHEDULED.value),
            ],
        )
        return response.get("numberOfRecordsUpdated") == 1

    def _execute(
        self, sql: str, parameters: list, include_result_metadata: bool = False
    ) -> dict:
        return self._rds_data.execute_statement(
            resourceArn=self._resource_arn,
            secretArn=self._secret_arn,
            database=self._database_name,
            sql=sql,
            parameters=parameters,
            includeResultMetadata=include_result_metadata,
        )
