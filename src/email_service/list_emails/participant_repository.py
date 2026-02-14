import json
import logging
import os
from decimal import Decimal  # Added import

import boto3
import time_util

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Participant table does not have JSONB columns
JSONB_COLUMNS = set()
TIMESTAMP_COLUMNS = {"rsvp_responded_at"}

DATABASE_NAME = os.environ["DATABASE_NAME"]
RDS_CLUSTER_ARN = os.environ["RDS_CLUSTER_ARN"]
RDS_CLUSTER_MASTER_USER_SECRET_ARN = os.environ["RDS_CLUSTER_MASTER_USER_SECRET_ARN"]


# Custom JSON encoder to handle Decimal types
class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects."""

    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


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


class ParticipantRepositoryError(Exception):
    """Participant repository error"""

    def __init__(self, message, sql=None, params=None, original_exception=None):
        super().__init__(message)
        self.sql = sql
        self.params = params
        self.original_exception = original_exception


class ParticipantRepository:
    """Participant data access layer"""

    def __init__(self):
        """Initialize participant repository"""
        self._rds_data = boto3.client("rds-data")
        self._database_name = DATABASE_NAME
        self._resource_arn = RDS_CLUSTER_ARN
        self._secret_arn = RDS_CLUSTER_MASTER_USER_SECRET_ARN

    def list_participants(self, filter_criteria_dict):
        """Get participant list"""
        # Build base SQL
        sql_string = "SELECT * FROM participant WHERE 1=1 "
        sql_parameters_list = []

        # Add filter conditions
        sql_string, sql_parameters_list = self._add_filtering_sql(
            sql_string_in=sql_string,
            sql_parameters_list_out=sql_parameters_list,
            filter_criteria_dict=filter_criteria_dict,
        )

        # Add sorting
        sort_by = filter_criteria_dict.get("sort_by", "participant_id")
        sort_order = filter_criteria_dict.get("sort_order", "ASC").upper()
        # Add a secondary, unique sort key to ensure stable pagination
        sql_string += f" ORDER BY {sort_by} {sort_order}, participant_id {sort_order}"

        # Add pagination
        sql_string, sql_parameters_list = self._add_pagination_sql(
            sql_string_in=sql_string,
            sql_parameters_list_out=sql_parameters_list,
            pagination_criteria_dict=filter_criteria_dict,
        )

        # Execute query
        participants = self._execute(sql_string, sql_parameters_list, fetch=True)

        return participants

    def count_participants(self, filter_criteria_dict):
        """Count participants matching the criteria"""
        sql_string = "SELECT COUNT(*) as count FROM participant WHERE 1=1 "
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

    def get_participant_by_id(self, run_id, participant_id):
        """Get a single participant by ID"""
        sql_string = (
            "SELECT * FROM participant WHERE run_id = :run_id AND participant_id = :participant_id"
        )
        sql_parameters = [
            {"name": "run_id", "value": {"stringValue": run_id}},
            {"name": "participant_id", "value": {"stringValue": participant_id}},
        ]
        results = self._execute(sql_string, sql_parameters, fetch=True)
        return results[0] if results else None

    def upsert_participant(self, participant):
        """Insert or update participant record"""
        try:
            # Participant table doesn't have created_at/updated_at columns
            # Only has: participant_id, run_id, email_id, rsvp_status, rsvp_responded_at
            
            columns = list(participant.keys())
            columns_str = ", ".join(columns)
            placeholders = ", ".join(f":{k}" for k in columns)
            
            # On conflict, update all columns except the primary key
            update_cols = [k for k in columns if k != "participant_id"]
            update_str = ", ".join(f"{k} = EXCLUDED.{k}" for k in update_cols)

            sql_string = f"""
                INSERT INTO participant ({columns_str})
                VALUES ({placeholders})
                ON CONFLICT (participant_id)
                DO UPDATE SET {update_str}
            """

            # Handle JSONB fields serialization before creating params
            for column in JSONB_COLUMNS:
                if column in participant and not isinstance(participant[column], str):
                    participant[column] = json.dumps(
                        participant[column],
                        cls=DecimalEncoder,  # Use DecimalEncoder here
                    )

            sql_parameters = []
            for k, v in participant.items():
                sql_parameters.append(
                    self._create_param(k, v)
                )  # Use the new _create_param

            self._execute(sql_string, sql_parameters)
            return participant.get("participant_id")
        except Exception as e:
            logger.error("Error saving participant: %s", e)
            return None

    def delete_participant(self, run_id, participant_id):
        """Delete participant"""
        sql_string = (
            "DELETE FROM participant WHERE run_id = :run_id AND participant_id = :participant_id"
        )
        sql_parameters = [
            {"name": "run_id", "value": {"stringValue": run_id}},
            {"name": "participant_id", "value": {"stringValue": participant_id}},
        ]
        self._execute(sql_string, sql_parameters)

    def update_rsvp_status(self, run_id, participant_id, rsvp_status):
        """Update participant RSVP status"""
        now = time_util.get_current_utc_time()
        sql_string = """
            UPDATE participant
            SET rsvp_status = :rsvp_status, rsvp_responded_at = :rsvp_responded_at
            WHERE run_id = :run_id AND participant_id = :participant_id
        """
        sql_parameters = [
            self._create_param("rsvp_status", rsvp_status),
            self._create_param("rsvp_responded_at", now),
            self._create_param("run_id", run_id),
            self._create_param("participant_id", participant_id),
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
                    "Could not parse timestamp string '%s' for key '%s'. Sending as string.",
                    value,
                    key,
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
            raise ParticipantRepositoryError(
                "SQL execution failed", sql, parameters, e
            ) from e
