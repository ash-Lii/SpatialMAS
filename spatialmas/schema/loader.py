from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from spatialmas.config import get_settings, resolve_path
from spatialmas.models import ColumnInfo, TableInfo


TABLE_HEADER_RE = re.compile(r"^##\s+([^.]+)\.(.+?)\s*$")
COLUMN_RE = re.compile(r"^\s+([A-Za-z0-9_]+)\s+(.+?)\s+(NULL|NOT NULL)\s*$")


@dataclass
class PromptRuleSection:
    """A named group of rules used to assemble a prompt section."""
    title: str = ""
    items: list[str] = field(default_factory=list)


@dataclass
class SchemaSelectionRules:
    """Rules for the schema-selection agent."""
    instruction: str = ""
    join_hints: list[str] = field(default_factory=list)
    timestamp_hints: list[str] = field(default_factory=list)
    response_format: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SchemaSelectionRules:
        return cls(
            instruction=d.get("instruction", ""),
            join_hints=list(d.get("join_hints", [])),
            timestamp_hints=list(d.get("timestamp_hints", [])),
            response_format=d.get("response_format", ""),
        )


@dataclass
class SQLGenerationRules:
    """Rules for the SQL-generation agent."""
    instruction: str = ""
    rules: list[str] = field(default_factory=list)
    quoting_instruction: str = ""
    response_format: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SQLGenerationRules:
        return cls(
            instruction=d.get("instruction", ""),
            rules=list(d.get("rules", [])),
            quoting_instruction=d.get("quoting_instruction", ""),
            response_format=d.get("response_format", ""),
        )


@dataclass
class PromptRules:
    """All prompt rules organised by agent role."""
    schema_selection: SchemaSelectionRules = field(default_factory=SchemaSelectionRules)
    sql_generation: SQLGenerationRules = field(default_factory=SQLGenerationRules)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PromptRules:
        # Support legacy flat structure where top-level keys were
        # join_hints / timestamp_hints / sql_generation_rules.
        sel = payload.get("schema_selection")
        gen = payload.get("sql_generation")
        if sel is not None or gen is not None:
            return cls(
                schema_selection=SchemaSelectionRules.from_dict(sel or {}),
                sql_generation=SQLGenerationRules.from_dict(gen or {}),
            )
        # Legacy: map flat keys into the new structure.
        return cls(
            schema_selection=SchemaSelectionRules(
                join_hints=list(payload.get("join_hints", [])),
                timestamp_hints=list(payload.get("timestamp_hints", [])),
            ),
            sql_generation=SQLGenerationRules(
                rules=list(payload.get("sql_generation_rules", [])),
            ),
        )


class SchemaRepository:
    def __init__(self) -> None:
        settings = get_settings()
        self.schema_path = resolve_path(settings.schema_path)
        self.rules_path = resolve_path(settings.schema_rules_path)

        self._tables: list[TableInfo] | None = None
        self._schema_text: str | None = None
        self._rules: PromptRules | None = None

    def load_tables(self) -> list[TableInfo]:
        if self._tables is not None:
            return self._tables

        self._tables = self._parse_tables(self.get_schema_text())
        return self._tables

    def get_table(self, schema_name: str, table_name: str) -> TableInfo | None:
        for table in self.load_tables():
            if table.schema_name == schema_name and table.table_name == table_name:
                return table
        return None

    def get_schema_text(self) -> str:
        if self._schema_text is not None:
            return self._schema_text

        if not self.schema_path.exists():
            raise FileNotFoundError(
                f"Schema file not found: {self.schema_path}. Run scripts/generate_schema.py first."
            )

        self._schema_text = self.schema_path.read_text(encoding="utf-8")
        return self._schema_text

    def get_rules(self) -> PromptRules:
        if self._rules is not None:
            return self._rules

        if self.rules_path.exists():
            payload = json.loads(self.rules_path.read_text(encoding="utf-8"))
        else:
            payload = {}

        self._rules = PromptRules.from_dict(payload)
        return self._rules

    @staticmethod
    def _parse_tables(schema_text: str) -> list[TableInfo]:
        tables: list[TableInfo] = []
        current_table: TableInfo | None = None

        for raw_line in schema_text.splitlines():
            line = raw_line.rstrip()

            header_match = TABLE_HEADER_RE.match(line)
            if header_match:
                current_table = TableInfo(
                    schema_name=header_match.group(1),
                    table_name=header_match.group(2),
                    columns=[],
                )
                tables.append(current_table)
                continue

            if line.startswith("## "):
                current_table = None
                continue

            if current_table is None:
                continue

            column_match = COLUMN_RE.match(line)
            if column_match:
                current_table.columns.append(
                    ColumnInfo(
                        name=column_match.group(1),
                        dtype=column_match.group(2),
                        nullable=(column_match.group(3) == "NULL"),
                    )
                )

        return tables


@lru_cache(maxsize=1)
def get_schema_repository() -> SchemaRepository:
    return SchemaRepository()