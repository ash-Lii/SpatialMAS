from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any


@dataclass
class ColumnInfo:
    name: str
    dtype: str
    nullable: bool = True


@dataclass
class TableInfo:
    schema_name: str
    table_name: str
    columns: list[ColumnInfo]

    @property
    def full_name(self) -> str:
        return f"{self.schema_name}.{self.table_name}"


@dataclass
class SchemaSelectionResult:
    schema_string: str
    selected_tables: list[TableInfo]
    reasoning: str
    original_count: int
    selected_count: int
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_string": self.schema_string,
            "selected_tables": [t.full_name for t in self.selected_tables],
            "reasoning": self.reasoning,
            "schema_reduction": f"{self.original_count} -> {self.selected_count}",
            "warnings": self.warnings,
        }


@dataclass
class SQLValidationResult:
    original_sql: str
    fixed_sql: str
    warnings: list[str]


@dataclass
class QueryExecutionResult:
    sql_original: str
    sql_executed: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    warnings: list[str]
    truncated: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QueryExecutionError:
    code: str
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details or {},
            }
        }


def to_json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return "<BINARY>"
    return value
