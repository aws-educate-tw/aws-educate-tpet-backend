import json
import logging
import os
from decimal import Decimal  # Added import

import boto3
import time_util

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

JSONB_COLUMNS = {
    "attachment_file_ids",
    "attachment_files",
    "bcc",
    "cc",
    "recipients",
    "sender",
    "spreadsheet_file",
    "template_file",
}
TIMESTAMP_COLUMNS = {"created_at"}  # Added for consistency

DATABASE_NAME = os.environ["DATABASE_NAME"]
RDS_CLUSTER_ARN = os.environ["RDS_CLUSTER_ARN"]
RDS_CLUSTER_MASTER_USER_SECRET_ARN = os.environ["RDS_CLUSTER_MASTER_USER_SECRET_ARN"]


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
            except json.JSONDecodeError:  # Changed to specific exception
                # If unable to parse as JSON, return the original string
                return value
        return value
    elif "longValue" in field:
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


# Custom JSON encoder to handle Decimal types
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)


class RunRepositoryError(Exception):
    """Run task repository error"""

    def __init__(self, message, sql=None, params=None, original_exception=None):
        super().__init__(message)
        self.sql = sql
        self.params = params
        self.original_exception = original_exception


class RunRepository:
    """Repository class for managing runs in PostgreSQL"""

    def __init__(self):
        """
        Initialize the repository with RDS Data API client.
        """
        self._rds_data = boto3.client("rds-data")
        self._database_name = DATABASE_NAME
        self._resource_arn = RDS_CLUSTER_ARN
        self._secret_arn = RDS_CLUSTER_MASTER_USER_SECRET_ARN

    def get_run_by_id(self, run_id: str) -> dict | None:
        """
        Retrieve a run by its ID from the PostgreSQL database.

        :param run_id: The ID of the run to retrieve
        :return: The run item, or None if not found
        """
        try:
            sql = "SELECT * FROM runs WHERE run_id = :run_id"
            params = [
                {"name": "run_id", "value": {"stringValue": run_id}},
            ]

            results = self._execute(sql, params, fetch=True)
            return results[0] if results else None
        except Exception as e:
            logger.error("Error getting run by ID: %s", e)
            return None

    def upsert_run(self, run: dict) -> str | None:
        """
        Insert or update a run in the PostgreSQL database.

        :param run: The run item to save
        :return: The ID of the saved run, or None if an error occurred
        """
        try:
            # Ensure creation time exists
            if "created_at" not in run:
                run["created_at"] = time_util.get_current_utc_time()

            # Generate year, month, day fields from creation time
            if "created_at" in run and (
                "created_year" not in run
                or "created_year_month" not in run
                or "created_year_month_day" not in run
            ):
                created_date = time_util.parse_iso8601_to_datetime(run["created_at"])
                run["created_year"] = created_date.strftime("%Y")
                run["created_year_month"] = created_date.strftime("%Y-%m")
                run["created_year_month_day"] = created_date.strftime("%Y-%m-%d")

            # Handle JSONB fields
            for column in JSONB_COLUMNS:
                if column in run and not isinstance(run[column], str):
                    run[column] = json.dumps(
                        run[column], cls=DecimalEncoder
                    )  # Use DecimalEncoder

            # Create SQL
            columns = list(run.keys())
            columns_str = ", ".join(columns)
            placeholders = ", ".join(f":{k}" for k in columns)

            # For UPDATE part, exclude run_id as primary key
            update_cols = [k for k in columns if k != "run_id"]
            update_str = ", ".join(f"{k} = EXCLUDED.{k}" for k in update_cols)

            sql = f"""
                INSERT INTO runs ({columns_str})
                VALUES ({placeholders})
                ON CONFLICT (run_id)
                DO UPDATE SET {update_str}
            """

            # Create parameters
            params = []
            for k, v in run.items():
                params.append(self._create_param(k, v))

            # Execute query
            self._execute(sql, params)
            return run["run_id"]
        except Exception as e:
            logger.error("Error upserting run: %s", e)
            return None

    def delete_run(self, run_id: str) -> None:
        """
        Delete a run by its ID from the PostgreSQL database.

        :param run_id: The ID of the run to delete
        """
        try:
            sql = "DELETE FROM runs WHERE run_id = :run_id"
            params = [
                {"name": "run_id", "value": {"stringValue": run_id}},
            ]

            self._execute(sql, params)
        except Exception as e:
            logger.error("Error deleting run: %s", e)

    def increment_success_email_count(self, run_id: str) -> None:
        """
        Increment the success_email_count for a run in the PostgreSQL database.

        :param run_id: The run ID to update
        """
        try:
            sql = """
                UPDATE runs
                SET success_email_count = success_email_count + 1
                WHERE run_id = :run_id
            """
            params = [
                {"name": "run_id", "value": {"stringValue": run_id}},
            ]

            self._execute(sql, params)
        except Exception as e:
            logger.error("Error updating success_email_count: %s", e)
            raise RunRepositoryError(
                "Error incrementing success email count", sql, params, e
            ) from e

    def update_run(self, run_id: str, update_data: dict) -> bool:
        """
        Update specific fields of a run in the PostgreSQL database.

        :param run_id: The ID of the run to update
        :param update_data: Dictionary containing fields to update
        :return: True if successful, False otherwise
        """
        try:
            # Handle JSONB fields
            for column in JSONB_COLUMNS:
                if column in update_data and not isinstance(update_data[column], str):
                    update_data[column] = json.dumps(
                        update_data[column], cls=DecimalEncoder
                    )  # Use DecimalEncoder

            # Build SET clause
            set_clauses = []
            params = []

            for key, value in update_data.items():
                set_clauses.append(f"{key} = :{key}")
                params.append(self._create_param(key, value))

            # Add run_id parameter
            params.append({"name": "run_id", "value": {"stringValue": run_id}})

            # Build SQL
            sql = f"UPDATE runs SET {', '.join(set_clauses)} WHERE run_id = :run_id"

            # Execute update
            self._execute(sql, params)
            return True
        except Exception as e:
            logger.error("Error updating run: %s", e)
            return False

    def list_runs(self, params):
        """
        Generic query method to list email tasks based on filter conditions

        :param params: Query parameters, may include filters, sorting and pagination
        :return: List of email tasks
        """
        # Build base SQL
        sql = "SELECT * FROM runs WHERE 1=1 "
        query_params = []

        # Add filter conditions
        sql, query_params = self._add_filtering_sql(
            sql=sql, params=query_params, query_params=params
        )

        # Add sorting
        sort_by = params.get("sort_by", "created_at")
        sort_order = params.get("sort_order", "DESC").upper()
        sql += f" ORDER BY {sort_by} {sort_order}"

        # Add pagination
        sql, query_params = self._add_pagination_sql(
            sql=sql, params=query_params, query_params=params
        )

        # Execute query
        return self._execute(sql, query_params, fetch=True)

    def count_runs(self, params):
        """
        Count the number of email tasks that match the conditions

        :param params: Query parameters, may include filter conditions
        :return: Number of email tasks
        """
        sql = "SELECT COUNT(*) as count FROM runs WHERE 1=1 "
        query_params = []

        # Add filter conditions
        sql, query_params = self._add_filtering_sql(
            sql=sql, params=query_params, query_params=params
        )

        # Execute query
        result = self._execute(sql, query_params, fetch=True)
        return result[0]["count"] if result else 0

    def _add_filtering_sql(self, sql, params, query_params):
        """Add filter conditions to SQL statement"""
        # Extract filter conditions from query_params
        filters = query_params.get("filters", {})

        # Also use other parameters from query_params as filter conditions
        for key, value in query_params.items():
            if (
                key not in ("filters", "page", "limit", "sort_by", "sort_order")
                and value is not None
            ):
                filters[key] = value

        # Build WHERE clause
        for key, value in filters.items():
            if value is not None:
                sql += f" AND {key} = :{key}"
                params.append(self._create_param(key, value))

        return sql, params

    def _add_pagination_sql(self, sql, params, query_params):
        """Add pagination to SQL statement"""
        limit = int(query_params.get("limit", 10))
        page = int(query_params.get("page", 1))
        offset = (page - 1) * limit

        sql += " LIMIT :limit OFFSET :offset"
        params.append({"name": "limit", "value": {"longValue": limit}})
        params.append({"name": "offset", "value": {"longValue": offset}})

        return sql, params

    def _create_param(self, key, value):
        """Create SQL parameter"""
        if value is None:
            return {"name": key, "value": {"isNull": True}}

        if isinstance(value, bool):
            return {"name": key, "value": {"booleanValue": value}}
        elif isinstance(value, int):
            return {"name": key, "value": {"longValue": value}}
        # For JSONB columns, 'value' should be a JSON string after json.dumps
        elif key in JSONB_COLUMNS and isinstance(
            value, str
        ):  # Check if key is in JSONB_COLUMNS
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
        # Default to stringValue for other types
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
                includeResultMetadata=(
                    True if fetch else False
                ),  # Added includeResultMetadata
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
            raise RunRepositoryError("SQL execution failed", sql, parameters, e) from e
