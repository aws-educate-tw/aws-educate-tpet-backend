import json
import logging
import os

import boto3
import time_util

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

JSONB_COLUMNS = {"bcc", "cc", "attachment_file_ids", "row_data"}


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
            except json.JSONDecodeError:
                # 如果無法解析為 JSON，返回原始字串
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


class EmailRepositoryError(Exception):
    """郵件儲存庫錯誤"""

    def __init__(self, message, sql=None, params=None, original_exception=None):
        super().__init__(message)
        self.sql = sql
        self.params = params
        self.original_exception = original_exception


class EmailRepository:
    """郵件數據訪問層"""

    def __init__(self):
        """初始化郵件儲存庫"""
        self._rds_data = boto3.client("rds-data")
        self._database_name = os.environ["DATABASE_NAME"]
        self._resource_arn = os.environ["CLUSTER_ARN"]
        self._secret_arn = os.environ["SECRET_ARN"]

    def list_emails(self, params):
        """獲取郵件列表"""
        # 構建基礎 SQL
        sql = "SELECT * FROM emails WHERE 1=1 "
        query_params = []

        # 添加過濾條件
        sql, query_params = self._add_filtering_sql(
            sql=sql, query_params=query_params, params=params
        )

        # 添加排序
        sort_by = params.get("sort_by", "created_at")
        sort_order = params.get("sort_order", "DESC").upper()
        sql += f" ORDER BY {sort_by} {sort_order}"

        # 添加分頁
        sql, query_params = self._add_pagination_sql(
            sql=sql, query_params=query_params, params=params
        )

        # 執行查詢
        emails = self._execute(sql, query_params, fetch=True)

        return emails

    def count_emails(self, params):
        """計算符合條件的郵件數量"""
        sql = "SELECT COUNT(*) as count FROM emails WHERE 1=1 "
        query_params = []

        # 添加過濾條件
        sql, query_params = self._add_filtering_sql(
            sql=sql, query_params=query_params, params=params
        )

        # 執行查詢
        result = self._execute(sql, query_params, fetch=True)
        return result[0]["count"] if result else 0

    def get_email_by_id(self, run_id, email_id):
        """通過ID獲取單個郵件"""
        sql = "SELECT * FROM emails WHERE run_id = :run_id AND email_id = :email_id"
        params = [
            {"name": "run_id", "value": {"stringValue": run_id}},
            {"name": "email_id", "value": {"stringValue": email_id}},
        ]
        results = self._execute(sql, params, fetch=True)
        return results[0] if results else None

    def upsert_email(self, email):
        """插入或更新郵件"""
        try:
            if "created_at" not in email:
                email["created_at"] = time_util.get_current_utc_time()

            columns = list(email.keys())
            columns_str = ", ".join(columns)
            placeholders = ", ".join(f":{k}" for k in columns)
            update_cols = [
                k for k in columns if k not in ("run_id", "email_id", "created_at")
            ]
            update_str = ", ".join(f"{k} = EXCLUDED.{k}" for k in update_cols)

            sql = f"""
                INSERT INTO emails ({columns_str})
                VALUES ({placeholders})
                ON CONFLICT (run_id, email_id)
                DO UPDATE SET {update_str}
            """

            params = []
            for k, v in email.items():
                if isinstance(v, dict | list):
                    params.append({"name": k, "value": {"stringValue": json.dumps(v)}})
                elif isinstance(v, str):
                    params.append({"name": k, "value": {"stringValue": v}})
                elif isinstance(v, bool):
                    params.append({"name": k, "value": {"booleanValue": v}})
                elif isinstance(v, int):
                    params.append({"name": k, "value": {"longValue": v}})
                elif v is None:
                    params.append({"name": k, "value": {"isNull": True}})
                else:
                    params.append({"name": k, "value": {"stringValue": str(v)}})

            self._execute(sql, params)
            return email.get("email_id")
        except Exception as e:
            logger.error("Error saving email: %s", e)
            return None

    def delete_email(self, run_id, email_id):
        """刪除郵件"""
        sql = "DELETE FROM emails WHERE run_id = :run_id AND email_id = :email_id"
        params = [
            {"name": "run_id", "value": {"stringValue": run_id}},
            {"name": "email_id", "value": {"stringValue": email_id}},
        ]
        self._execute(sql, params)

    def update_email_status(self, run_id, email_id, status):
        """更新郵件狀態"""
        now = time_util.get_current_utc_time()
        sql = """
            UPDATE emails
            SET status = :status, sent_at = :sent_at, updated_at = :updated_at
            WHERE run_id = :run_id AND email_id = :email_id
        """
        params = [
            {"name": "status", "value": {"stringValue": status}},
            {"name": "sent_at", "value": {"stringValue": now}},
            {"name": "updated_at", "value": {"stringValue": now}},
            {"name": "run_id", "value": {"stringValue": run_id}},
            {"name": "email_id", "value": {"stringValue": email_id}},
        ]
        self._execute(sql, params)

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
            raise EmailRepositoryError(
                "SQL execution failed", sql, parameters, e
            ) from e
