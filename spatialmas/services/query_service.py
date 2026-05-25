from __future__ import annotations

import re

from snowflake.connector.errors import ProgrammingError

from spatialmas.config import get_settings
from spatialmas.infra.snowflake_client import SnowflakeClient
from spatialmas.models import QueryExecutionResult
from spatialmas.services.sql_service import SQLValidationService


class QueryService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = SnowflakeClient()

    def execute_query(self, sql_query: str, limit: int | None = None) -> QueryExecutionResult:
        safe_limit = self._resolve_limit(limit)

        validated = SQLValidationService.validate_and_fix_sql(sql_query)
        executable_sql = SQLValidationService.ensure_limit(validated.fixed_sql, safe_limit)
        warnings = list(validated.warnings)

        try:
            columns, rows, truncated = self.client.execute_read_query(executable_sql, safe_limit)
        except ProgrammingError as exc:
            retry_sql, retry_warning = self._retry_invalid_identifier(executable_sql, str(exc))
            if retry_sql is None:
                raise
            columns, rows, truncated = self.client.execute_read_query(retry_sql, safe_limit)
            executable_sql = retry_sql
            if retry_warning:
                warnings.append(retry_warning)

        return QueryExecutionResult(
            sql_original=validated.original_sql,
            sql_executed=executable_sql,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            warnings=warnings,
            truncated=truncated,
        )

    def _resolve_limit(self, requested: int | None) -> int:
        if requested is None:
            return self.settings.default_result_limit
        return max(1, min(requested, self.settings.max_result_limit))

    @staticmethod
    def _retry_invalid_identifier(sql: str, error_message: str) -> tuple[str | None, str | None]:
        match = re.search(r"invalid identifier '([^']+)'", error_message, re.IGNORECASE)
        if not match:
            return None, None

        identifier = match.group(1).strip().strip('"').lower()
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", identifier):
            return None, None

        pattern = re.compile(rf'(?<!")\b{re.escape(identifier)}\b(?!")', re.IGNORECASE)
        if not pattern.search(sql):
            return None, None

        quoted_sql = pattern.sub(f'"{identifier}"', sql)
        return quoted_sql, f'Retried query after quoting invalid identifier "{identifier}"'
