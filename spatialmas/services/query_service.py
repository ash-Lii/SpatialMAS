from __future__ import annotations

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

        columns, rows, truncated = self.client.execute_read_query(executable_sql, safe_limit)
        return QueryExecutionResult(
            sql_original=validated.original_sql,
            sql_executed=executable_sql,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            warnings=validated.warnings,
            truncated=truncated,
        )

    def _resolve_limit(self, requested: int | None) -> int:
        if requested is None:
            return self.settings.default_result_limit
        return max(1, min(requested, self.settings.max_result_limit))
