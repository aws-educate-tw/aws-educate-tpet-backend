import json
import logging
import os

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


def parse_field(col_name, field):
    """
    解析 RDS Data API 返回的字段值

    :param col_name: 字段名稱
    :param field: RDS Data API 返回的字段值
    :return: 轉換後的 Python 類型值
    """
    # 處理 NULL 值
    if "isNull" in field and field["isNull"]:
        return None

    # 處理基本類型
    if "stringValue" in field:
        value = field["stringValue"]
        # 處理 JSONB 類型
        if col_name in JSONB_COLUMNS:
            try:
                return json.loads(value)
            except Exception:
                # 如果無法解析為 JSON，返回原始字串
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

    # 處理數組類型
    elif "arrayValue" in field:
        array = field["arrayValue"]

        # 處理各種數組類型
        if "stringValues" in array:
            return array["stringValues"]
        elif "longValues" in array:
            return array["longValues"]
        elif "doubleValues" in array:
            return array["doubleValues"]
        elif "booleanValues" in array:
            return array["booleanValues"]
        elif "arrayValues" in array:
            # 遞歸處理嵌套數組
            return [parse_field(col_name, v) for v in array["arrayValues"]]
        # 空數組
        return []

    # 如果無法識別類型，返回原始字段
    return field


class RunRepositoryError(Exception):
    """運行任務儲存庫錯誤"""

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
        self._database_name = os.environ["DATABASE_NAME"]
        self._resource_arn = os.environ["CLUSTER_ARN"]
        self._secret_arn = os.environ["SECRET_ARN"]

    def query_runs_by_created_year(
        self,
        created_year: str,
        limit: int = 10,
        offset: int = 0,
        sort_order: str = "DESC",
    ) -> list[dict]:
        """
        Query runs from the PostgreSQL database based on created year and pagination parameters.

        :param created_year: The created year to filter by
        :param limit: The maximum number of items to return
        :param offset: The offset for pagination
        :param sort_order: The sort order, either 'ASC' or 'DESC'
        :return: List of run items
        """
        try:
            # 構建基本 SQL
            sql = "SELECT * FROM runs WHERE created_year = :created_year"
            params = [
                {"name": "created_year", "value": {"stringValue": created_year}},
            ]

            # 添加排序
            sql += f" ORDER BY created_at {sort_order}"

            # 添加分頁
            sql += " LIMIT :limit OFFSET :offset"
            params.extend(
                [
                    {"name": "limit", "value": {"longValue": limit}},
                    {"name": "offset", "value": {"longValue": offset}},
                ]
            )

            # 執行查詢
            return self._execute(sql, params, fetch=True)
        except Exception as e:
            logger.error("Error querying runs by created year: %s", e)
            raise RunRepositoryError("Error querying runs", sql, params, e) from e

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
            # 確保有創建時間
            if "created_at" not in run:
                run["created_at"] = time_util.get_current_utc_time()

            # 從創建時間生成年、月、日字段
            if "created_at" in run and (
                "created_year" not in run
                or "created_year_month" not in run
                or "created_year_month_day" not in run
            ):
                created_date = time_util.parse_iso8601_to_datetime(run["created_at"])
                run["created_year"] = created_date.strftime("%Y")
                run["created_year_month"] = created_date.strftime("%Y-%m")
                run["created_year_month_day"] = created_date.strftime("%Y-%m-%d")

            # 處理 JSONB 字段
            for column in JSONB_COLUMNS:
                if column in run and not isinstance(run[column], str):
                    run[column] = json.dumps(run[column])

            # 建立 SQL
            columns = list(run.keys())
            columns_str = ", ".join(columns)
            placeholders = ", ".join(f":{k}" for k in columns)

            # 對於 UPDATE 部分，排除 run_id 作為主鍵
            update_cols = [k for k in columns if k != "run_id"]
            update_str = ", ".join(f"{k} = EXCLUDED.{k}" for k in update_cols)

            sql = f"""
                INSERT INTO runs ({columns_str})
                VALUES ({placeholders})
                ON CONFLICT (run_id)
                DO UPDATE SET {update_str}
            """

            # 建立參數
            params = []
            for k, v in run.items():
                params.append(self._create_param(k, v))

            # 執行查詢
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
            # 處理 JSONB 字段
            for column in JSONB_COLUMNS:
                if column in update_data and not isinstance(update_data[column], str):
                    update_data[column] = json.dumps(update_data[column])

            # 構建 SET 子句
            set_clauses = []
            params = []

            for key, value in update_data.items():
                set_clauses.append(f"{key} = :{key}")
                params.append(self._create_param(key, value))

            # 添加 run_id 參數
            params.append({"name": "run_id", "value": {"stringValue": run_id}})

            # 構建 SQL
            sql = f"UPDATE runs SET {', '.join(set_clauses)} WHERE run_id = :run_id"

            # 執行更新
            self._execute(sql, params)
            return True
        except Exception as e:
            logger.error("Error updating run: %s", e)
            return False

    def list_runs(self, params):
        """
        通用查詢方法，根據過濾條件列出郵件任務

        :param params: 查詢參數，可包含過濾條件、排序和分頁
        :return: 郵件任務列表
        """
        # 構建基礎 SQL
        sql = "SELECT * FROM runs WHERE 1=1 "
        query_params = []

        # 添加過濾條件
        sql, query_params = self._add_filtering_sql(
            sql=sql, params=query_params, query_params=params
        )

        # 添加排序
        sort_by = params.get("sort_by", "created_at")
        sort_order = params.get("sort_order", "DESC").upper()
        sql += f" ORDER BY {sort_by} {sort_order}"

        # 添加分頁
        sql, query_params = self._add_pagination_sql(
            sql=sql, params=query_params, query_params=params
        )

        # 執行查詢
        return self._execute(sql, query_params, fetch=True)

    def count_runs(self, params):
        """
        計算符合條件的郵件任務數量

        :param params: 查詢參數，可包含過濾條件
        :return: 郵件任務數量
        """
        sql = "SELECT COUNT(*) as count FROM runs WHERE 1=1 "
        query_params = []

        # 添加過濾條件
        sql, query_params = self._add_filtering_sql(
            sql=sql, params=query_params, query_params=params
        )

        # 執行查詢
        result = self._execute(sql, query_params, fetch=True)
        return result[0]["count"] if result else 0

    def _add_filtering_sql(self, sql, params, query_params):
        """添加過濾條件到SQL語句"""
        # 從 query_params 中提取過濾條件
        filters = query_params.get("filters", {})

        # 將 query_params 中的其他參數也作為過濾條件
        for key, value in query_params.items():
            if (
                key not in ("filters", "page", "limit", "sort_by", "sort_order")
                and value is not None
            ):
                filters[key] = value

        # 構建 WHERE 子句
        for key, value in filters.items():
            if value is not None:
                sql += f" AND {key} = :{key}"
                params.append(self._create_param(key, value))

        return sql, params

    def _add_pagination_sql(self, sql, params, query_params):
        """添加分頁到SQL語句"""
        limit = int(query_params.get("limit", 10))
        page = int(query_params.get("page", 1))
        offset = (page - 1) * limit

        sql += " LIMIT :limit OFFSET :offset"
        params.append({"name": "limit", "value": {"longValue": limit}})
        params.append({"name": "offset", "value": {"longValue": offset}})

        return sql, params

    def _create_param(self, key, value):
        """創建SQL參數"""
        if isinstance(value, int):
            return {"name": key, "value": {"longValue": value}}
        elif isinstance(value, bool):
            return {"name": key, "value": {"booleanValue": value}}
        elif value is None:
            return {"name": key, "value": {"isNull": True}}
        else:
            return {"name": key, "value": {"stringValue": str(value)}}

    def _execute(self, sql, parameters, fetch=False):
        """執行SQL查詢"""
        try:
            if os.getenv("DEBUG_SQL", "false").lower() == "true":
                logger.debug("Executing SQL:\n%s\nParams:\n%s", sql, parameters)

            response = self._rds_data.execute_statement(
                resourceArn=self._resource_arn,
                secretArn=self._secret_arn,
                database=self._database_name,
                sql=sql,
                parameters=parameters,
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
