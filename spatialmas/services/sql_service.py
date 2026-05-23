from __future__ import annotations

import re
from typing import Any

from spatialmas.infra.llm_client import create_llm
from spatialmas.models import SQLValidationResult
from spatialmas.schema.loader import get_schema_repository


MICROSECOND_YEAR_START = {
    2013: 1356998400000000,
    2014: 1388534400000000,
    2015: 1420070400000000,
    2016: 1451606400000000,
    2017: 1483228800000000,
    2018: 1514764800000000,
    2019: 1546300800000000,
    2020: 1577836800000000,
    2021: 1609459200000000,
    2022: 1640995200000000,
}


class SQLGenerationService:
    def __init__(self, temperature: float = 0) -> None:
        self.repo = get_schema_repository()
        self.llm = create_llm(temperature=temperature)

    def generate_sql(self, question: str, schema_string: str) -> str:
        rules = self.repo.get_rules()
        gen_rules = rules.sql_generation

        lines = [gen_rules.instruction or "You are a Snowflake SQL expert."]
        lines.append("")
        lines.append("## Schema")
        lines.append(schema_string)
        lines.append("")

        if gen_rules.rules:
            lines.append("## Rules")
            for rule in gen_rules.rules:
                lines.append(f"- {rule}")
            lines.append("")

        if gen_rules.quoting_instruction:
            lines.append("## Important: column name quoting")
            lines.append(gen_rules.quoting_instruction)
            lines.append("")

        lines.append("## User question")
        lines.append(question)
        lines.append("")

        if gen_rules.response_format:
            lines.append(gen_rules.response_format)
        else:
            lines.append("Output SQL only. Use markdown SQL fence.")

        prompt = "\n".join(lines)
        response = self.llm.invoke(prompt)
        return self._extract_sql(response.content)

    @staticmethod
    def _extract_sql(content: Any) -> str:
        text = str(content).strip()
        match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text


class SQLValidationService:
    READ_ONLY_PREFIXES = ("SELECT", "WITH")
    FORBIDDEN_KEYWORDS = (
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "MERGE",
        "GRANT",
        "REVOKE",
        "CALL",
        "COPY",
    )

    @classmethod
    def validate_and_fix_sql(cls, sql_query: str) -> SQLValidationResult:
        original = sql_query.strip()
        fixed = original
        warnings: list[str] = []

        cls._enforce_read_only(fixed)

        # Convert BETWEEN year-year ranges into microsecond timestamp ranges.
        fixed, year_warning = cls._rewrite_year_between(fixed)
        if year_warning:
            warnings.append(year_warning)

        # Soft warning for likely microsecond timestamp fields.
        if re.search(r'\b\w*(date|time|timestamp)\w*\b', fixed, re.IGNORECASE):
            if "/1000000" not in fixed.replace(" ", ""):
                warnings.append(
                    "Detected potential timestamp fields. If values are microseconds, use /1000000 before TO_TIMESTAMP"
                )

        return SQLValidationResult(original_sql=original, fixed_sql=fixed, warnings=warnings)

    @classmethod
    def _enforce_read_only(cls, sql: str) -> None:
        sql_no_comments = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
        sql_no_comments = re.sub(r"/\*.*?\*/", "", sql_no_comments, flags=re.DOTALL)
        first_token_match = re.search(r"\b([A-Za-z]+)\b", sql_no_comments)
        first_token = first_token_match.group(1).upper() if first_token_match else ""

        if first_token not in cls.READ_ONLY_PREFIXES:
            raise ValueError("Only read-only SQL is allowed (must start with SELECT or WITH)")

        upper_sql = sql_no_comments.upper()
        for keyword in cls.FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{keyword}\b", upper_sql):
                raise ValueError(f"Forbidden SQL keyword in read-only mode: {keyword}")

    @staticmethod
    def ensure_limit(sql: str, limit: int) -> str:
        if re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
            return sql
        return f"{sql.rstrip(';')} LIMIT {limit}"

    @staticmethod
    def _rewrite_year_between(sql: str) -> tuple[str, str | None]:
        pattern = re.compile(r"BETWEEN\s+(\d{4})\s+AND\s+(\d{4})", re.IGNORECASE)

        def repl(match: re.Match[str]) -> str:
            start_year = int(match.group(1))
            end_year = int(match.group(2))
            start_ts = MICROSECOND_YEAR_START.get(start_year)
            end_ts = MICROSECOND_YEAR_START.get(end_year + 1)
            if start_ts and end_ts:
                return f"BETWEEN {start_ts} AND {end_ts - 1}"
            return match.group(0)

        new_sql = pattern.sub(repl, sql)
        if new_sql != sql:
            return new_sql, "Converted year-based BETWEEN filter to microsecond timestamps"
        return new_sql, None