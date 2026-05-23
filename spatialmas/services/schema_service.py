from __future__ import annotations

import json
import re
from typing import Any

from spatialmas.infra.llm_client import create_llm
from spatialmas.models import SchemaSelectionResult, TableInfo
from spatialmas.schema.loader import get_schema_repository


class SchemaSelectionService:
    def __init__(self, temperature: float = 0) -> None:
        self.repo = get_schema_repository()
        self.llm = create_llm(temperature=temperature)

    def select_relevant_schema(self, question: str) -> SchemaSelectionResult:
        all_tables = self.repo.load_tables()
        schema_text = self.repo.get_schema_text()
        rules = self.repo.get_rules()

        prompt = self._build_prompt(question, schema_text, rules.schema_selection)
        response = self.llm.invoke(prompt)
        payload = self._parse_json_content(response.content)

        warnings: list[str] = []
        selected_tables_raw = payload.get("selected_tables", []) if isinstance(payload, dict) else []
        if not selected_tables_raw:
            warnings.append("LLM schema selection parsing failed; fallback keyword selection applied")
            selected_tables = self._fallback_select(question)
            reasoning = "Fallback keyword matching"
        else:
            selected_tables = self._build_table_selection(selected_tables_raw)
            reasoning = str(payload.get("reasoning", ""))

        schema_string = self._format_schema(selected_tables)

        return SchemaSelectionResult(
            schema_string=schema_string,
            selected_tables=selected_tables,
            reasoning=reasoning,
            original_count=len(all_tables),
            selected_count=len(selected_tables),
            warnings=warnings,
        )

    @staticmethod
    def _build_prompt(question: str, schema_text: str, sel_rules) -> str:
        lines = [sel_rules.instruction or "You are a database schema selection expert."]
        lines.append("")
        lines.append("## Schema")
        lines.append(schema_text)
        lines.append("")

        if sel_rules.join_hints:
            lines.append("## Critical join hints")
            for hint in sel_rules.join_hints:
                lines.append(f"- {hint}")
            lines.append("")

        if sel_rules.timestamp_hints:
            lines.append("## Timestamp hints")
            for hint in sel_rules.timestamp_hints:
                lines.append(f"- {hint}")
            lines.append("")

        lines.append("## User question")
        lines.append(question)
        lines.append("")

        if sel_rules.response_format:
            lines.append(sel_rules.response_format)
        else:
            lines.append(
                'Return JSON only:\n'
                '{\n'
                '  "selected_tables": [\n'
                '    {"schema_name": "SCHEMA", "table_name": "TABLE", "columns": ["col_a", "col_b"]}\n'
                '  ],\n'
                '  "reasoning": "short reasoning"\n'
                '}'
            )

        return "\n".join(lines)

    @staticmethod
    def _parse_json_content(content: Any) -> dict[str, Any]:
        text = str(content)

        fenced = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def _build_table_selection(self, selected_tables: list[dict[str, Any]]) -> list[TableInfo]:
        results: list[TableInfo] = []
        for item in selected_tables:
            schema_name = str(item.get("schema_name", "")).strip()
            table_name = str(item.get("table_name", "")).strip()
            selected_columns = set(item.get("columns", []))

            table = self.repo.get_table(schema_name, table_name)
            if table is None:
                continue

            columns = [col for col in table.columns if col.name in selected_columns]
            if not columns:
                columns = table.columns

            results.append(
                TableInfo(schema_name=table.schema_name, table_name=table.table_name, columns=columns)
            )

        return results

    def _fallback_select(self, question: str) -> list[TableInfo]:
        q = question.lower()
        candidates: list[TableInfo] = []
        for table in self.repo.load_tables():
            score = 0
            if table.table_name.lower() in q:
                score += 3
            if table.schema_name.lower().replace("san_francisco_", "") in q:
                score += 2
            for col in table.columns:
                if col.name.lower() in q:
                    score += 1
            if score > 0:
                candidates.append(table)

        if not candidates:
            return self.repo.load_tables()[:3]

        return candidates[:5]

    @staticmethod
    def _format_schema(tables: list[TableInfo]) -> str:
        lines: list[str] = []
        for table in tables:
            lines.append(f"-- {table.full_name}")
            for col in table.columns:
                lines.append(f'  "{col.name}" {col.dtype}')
            lines.append("")
        return "\n".join(lines).strip()