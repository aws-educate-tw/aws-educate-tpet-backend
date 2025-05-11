import json
import logging
import os
from decimal import Decimal  # Added import

import boto3
import time_util

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

JSONB_COLUMNS = {"bcc", "cc", "attachment_file_ids", "row_data"}
TIMESTAMP_COLUMNS = {"created_at", "sent_at", "updated_at"}

DATABASE_NAME = os.environ["DATABASE_NAME"]
RDS_CLUSTER_ARN = os.environ["RDS_CLUSTER_ARN"]
RDS_CLUSTER_MASTER_USER_SECRET_ARN = os.environ["RDS_CLUSTER_MASTER_USER_SECRET_ARN"]


# Custom JSON encoder to handle Decimal types
class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects."""

    def default(self, obj: object) -> object:
        if isinstance(obj, Decimal):
            return str(obj)  # Changed to str(obj) for precision
        return super().default(obj)


def parse_field(col_name, field):
    """
    Parse field values returned by RDS Data API

    :param col_name: Field name
    :param field: Field value returned by RDS Data API
    :return: Converted Python type value
    """
    # Handle NULL values
    if "isNull" in field and field["isNull"]:
        return None

    # Handle basic types
    if "stringValue" in field:
        value = field["stringValue"]
        # Handle JSONB type
        if col_name in JSONB_COLUMNS:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # If cannot be parsed as JSON, return the original string
                return value
        return value
    if "longValue" in field:
        return field["longValue"]
    elif "doubleValue" in field:
        return field["doubleValue"]
    elif "booleanValue" in field:
        return field["booleanValue"]
    elif "blobValue" in field:
        return field["blobValue"]

    # Handle array types
    elif "arrayValue" in field:
        array = field["arrayValue"]

        # Handle various array types
        if "stringValues" in array:
            return array["stringValues"]
        elif "longValues" in array:
            return array["longValues"]
        elif "doubleValues" in array:
            return array["doubleValues"]
        elif "booleanValues" in array:
            return array["booleanValues"]
        elif "arrayValues" in array:
            # Recursively process nested arrays
            return [parse_field(col_name, v) for v in array["arrayValues"]]
        # Empty array
        return []

    # If type cannot be identified, return the original field
    return field


class EmailRepositoryError(Exception):
    """Email repository error"""

    def __init__(self, message, sql=None, params=None, original_exception=None):
        super().__init__(message)
        self.sql = sql
        self.params = params
        self.original_exception = original_exception


class EmailRepository:
    """Email data access layer"""

    def __init__(self):
        """Initialize email repository"""
        self._rds_data = boto3.client("rds-data")
        self._database_name = DATABASE_NAME
        self._resource_arn = RDS_CLUSTER_ARN
        self._secret_arn = RDS_CLUSTER_MASTER_USER_SECRET_ARN

    def list_emails(self, filter_criteria_dict):
        """Get email list"""
        # Build base SQL
        sql_string = "SELECT * FROM emails WHERE 1=1 "
        sql_parameters_list = []

        # Add filter conditions
        sql_string, sql_parameters_list = self._add_filtering_sql(
            sql_string_in=sql_string,
            sql_parameters_list_out=sql_parameters_list,
            filter_criteria_dict=filter_criteria_dict,
        )

        # Add sorting
        sort_by = filter_criteria_dict.get("sort_by", "created_at")
        sort_order = filter_criteria_dict.get("sort_order", "DESC").upper()
        sql_string += f" ORDER BY {sort_by} {sort_order}"

        # Add pagination
        sql_string, sql_parameters_list = self._add_pagination_sql(
            sql_string_in=sql_string,
            sql_parameters_list_out=sql_parameters_list,
            pagination_criteria_dict=filter_criteria_dict,
        )

        # Execute query
        emails = self._execute(sql_string, sql_parameters_list, fetch=True)

        return emails

    def count_emails(self, filter_criteria_dict):
        """Count emails matching the criteria"""
        sql_string = "SELECT COUNT(*) as count FROM emails WHERE 1=1 "
        sql_parameters_list = []

        # Add filter conditions
        sql_string, sql_parameters_list = self._add_filtering_sql(
            sql_string_in=sql_string,
            sql_parameters_list_out=sql_parameters_list,
            filter_criteria_dict=filter_criteria_dict,
        )

        # Execute query
        result = self._execute(sql_string, sql_parameters_list, fetch=True)
        return result[0]["count"] if result else 0

    def get_email_by_id(self, run_id, email_id):
        """Get a single email by ID"""
        sql_string = (
            "SELECT * FROM emails WHERE run_id = :run_id AND email_id = :email_id"
        )
        sql_parameters = [
            {"name": "run_id", "value": {"stringValue": run_id}},
            {"name": "email_id", "value": {"stringValue": email_id}},
        ]
        results = self._execute(sql_string, sql_parameters, fetch=True)
        return results[0] if results else None

    def upsert_email(self, email):
        """Insert or update email"""
        try:
            now_utc = time_util.get_current_utc_time()
            if "created_at" not in email:
                email["created_at"] = now_utc
            email["updated_at"] = now_utc  # Always set/update updated_at

            columns = list(email.keys())
            columns_str = ", ".join(columns)
            placeholders = ", ".join(f":{k}" for k in columns)
            # Ensure updated_at is part of the update set
            # run_id and email_id are part of the conflict target, created_at should not change on update
            update_cols = [
                k for k in columns if k not in ("run_id", "email_id", "created_at")
            ]
            # If 'updated_at' was not already in update_cols (e.g. if it was in the exclusion list before)
            # ensure it's added for the SET clause.
            # However, by adding it to the email dict unconditionally above, it will be in 'columns'
            # and thus included here if not in the exclusion list.
            # The current exclusion list is ("run_id", "email_id", "created_at"), so updated_at will be included.

            update_str = ", ".join(f"{k} = EXCLUDED.{k}" for k in update_cols)
            # If we wanted to be absolutely certain updated_at is set to current time on update:
            # update_clauses = [f"{k} = EXCLUDED.{k}" for k in update_cols if k != "updated_at"]
            # update_clauses.append("updated_at = CURRENT_TIMESTAMP") # Or use EXCLUDED.updated_at if now_utc is passed
            # update_str = ", ".join(update_clauses)
            # For now, relying on EXCLUDED.updated_at (which we set to now_utc) is fine.

            sql_string = f"""
                INSERT INTO emails ({columns_str})
                VALUES ({placeholders})
                ON CONFLICT (email_id)
                DO UPDATE SET {update_str}
            """

            # Handle JSONB fields serialization before creating params
            for column in JSONB_COLUMNS:
                if column in email and not isinstance(email[column], str):
                    email[column] = json.dumps(
                        email[column],
                        cls=DecimalEncoder,  # Use DecimalEncoder here
                    )

            sql_parameters = []
            for k, v in email.items():
                sql_parameters.append(
                    self._create_param(k, v)
                )  # Use the new _create_param

            self._execute(sql_string, sql_parameters)
            return email.get("email_id")
        except Exception as e:
            logger.error("Error saving email: %s", e)
            return None

    def delete_email(self, run_id, email_id):
        """Delete email"""
        sql_string = (
            "DELETE FROM emails WHERE run_id = :run_id AND email_id = :email_id"
        )
        sql_parameters = [
            {"name": "run_id", "value": {"stringValue": run_id}},
            {"name": "email_id", "value": {"stringValue": email_id}},
        ]
        self._execute(sql_string, sql_parameters)

    def update_email_status(self, run_id, email_id, status):
        """Update email status"""
        now = time_util.get_current_utc_time()
        sql_string = """
            UPDATE emails
            SET status = :status, sent_at = :sent_at, updated_at = :updated_at
            WHERE run_id = :run_id AND email_id = :email_id
        """
        sql_parameters = [
            self._create_param("status", status),
            self._create_param(
                "sent_at", now
            ),  # 'now' is from time_util.get_current_utc_time()
            self._create_param(
                "updated_at", now
            ),  # 'now' is from time_util.get_current_utc_time()
            self._create_param("run_id", run_id),
            self._create_param("email_id", email_id),
        ]
        self._execute(sql_string, sql_parameters)

    def _add_filtering_sql(
        self,
        sql_string_in: str,
        sql_parameters_list_out: list,
        filter_criteria_dict: dict,
    ):
        """Add filter conditions to SQL statement"""
        current_sql_string = sql_string_in
        # Extract filter conditions from filter_criteria_dict
        # The 'filters' key itself is not expected directly inside filter_criteria_dict based on usage.
        # We iterate directly over filter_criteria_dict for relevant keys.

        processed_filters = {}
        for key, value in filter_criteria_dict.items():
            if (
                key
                not in (
                    "page",
                    "limit",
                    "sort_by",
                    "sort_order",
                )  # Exclude pagination/sorting keys
                and value is not None
            ):
                processed_filters[key] = value

        # Build WHERE clause
        for key, value in processed_filters.items():
            if value is not None:  # Redundant check, but kept for safety
                current_sql_string += f" AND {key} = :{key}"
                sql_parameters_list_out.append(self._create_param(key, value))

        return current_sql_string, sql_parameters_list_out

    def _add_pagination_sql(
        self,
        sql_string_in: str,
        sql_parameters_list_out: list,
        pagination_criteria_dict: dict,
    ):
        """Add pagination to SQL statement"""
        current_sql_string = sql_string_in
        limit = int(pagination_criteria_dict.get("limit", 10))
        page = int(pagination_criteria_dict.get("page", 1))
        offset = (page - 1) * limit

        current_sql_string += " LIMIT :limit OFFSET :offset"
        sql_parameters_list_out.append({"name": "limit", "value": {"longValue": limit}})
        sql_parameters_list_out.append(
            {"name": "offset", "value": {"longValue": offset}}
        )

        return current_sql_string, sql_parameters_list_out

    def _create_param(self, key, value):
        """Create SQL parameter"""
        if value is None:
            return {"name": key, "value": {"isNull": True}}

        if isinstance(value, bool):
            return {"name": key, "value": {"booleanValue": value}}
        elif isinstance(value, int):
            return {"name": key, "value": {"longValue": value}}
        elif key in JSONB_COLUMNS and isinstance(value, str):
            return {
                "name": key,
                "value": {"stringValue": value},
                "typeHint": "JSON",
            }
        elif key in TIMESTAMP_COLUMNS and isinstance(value, str):
            # Assume value is an ISO 8601 string from time_util
            try:
                dt_obj = time_util.parse_iso8601_to_datetime(value)
                formatted_ts = time_util.format_datetime_for_rds(dt_obj)
                return {
                    "name": key,
                    "value": {"stringValue": formatted_ts},
                    "typeHint": "TIMESTAMP",
                }
            except ValueError:  # Should not happen if time_util is used consistently
                logger.warning(
                    f"Could not parse timestamp string '{value}' for key '{key}'. Sending as string."
                )
                return {"name": key, "value": {"stringValue": str(value)}}
        else:
            return {"name": key, "value": {"stringValue": str(value)}}

    def _execute(self, sql, parameters, fetch=False):
        """Execute SQL query"""
        try:
            if os.getenv("DEBUG_SQL", "false").lower() == "true":
                logger.debug("Executing SQL:\n%s\nParams:\n%s", sql, parameters)

            response = self._rds_data.execute_statement(
                resourceArn=self._resource_arn,
                secretArn=self._secret_arn,
                database=self._database_name,
                sql=sql,
                parameters=parameters,
                includeResultMetadata=True if fetch else False,
            )

            if not fetch:
                return None

            columns = [col["name"] for col in response["columnMetadata"]]
            return [
                {
                    col: parse_field(col, val)
                    for col, val in zip(columns, row, strict=False)
                }
                for row in response["records"]
            ]
        except Exception as e:
            logger.error(
                "SQL execution failed: %s\nSQL: %s\nParams: %s", e, sql, parameters
            )
            raise EmailRepositoryError(
                "SQL execution failed", sql, parameters, e
            ) from e
