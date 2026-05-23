from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import snowflake.connector

from spatialmas.config import get_settings, require_snowflake_settings
from spatialmas.models import to_json_safe


class SnowflakeClient:
    def __init__(self) -> None:
        require_snowflake_settings()
        self.settings = get_settings()

    def _connect_args(self) -> dict[str, Any]:
        args: dict[str, Any] = {
            "user": self.settings.snowflake_user,
            "password": self.settings.snowflake_password,
            "account": self.settings.snowflake_account,
            "database": self.settings.snowflake_database,
        }
        return args

    @contextmanager
    def connection(self) -> Iterator[Any]:
        conn = snowflake.connector.connect(**self._connect_args())
        try:
            yield conn
        finally:
            conn.close()

    def execute_read_query(self, sql: str, fetch_limit: int) -> tuple[list[str], list[list[Any]], bool]:
        with self.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {self.settings.query_timeout_seconds}"
                )
                cur.execute(sql)
                columns = [desc[0] for desc in cur.description] if cur.description else []

                rows_raw = cur.fetchmany(fetch_limit)
                rows = [[to_json_safe(col) for col in row] for row in rows_raw]

                truncated = len(rows_raw) >= fetch_limit
                return columns, rows, truncated
            finally:
                cur.close()
