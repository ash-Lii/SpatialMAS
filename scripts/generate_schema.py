from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time
from decimal import Decimal
from pathlib import Path
from typing import Any

import snowflake.connector
from dotenv import load_dotenv


load_dotenv()


@dataclass
class ColumnInfo:
    name: str
    dtype: str
    nullable: bool


@dataclass
class TableInfo:
    schema_name: str
    table_name: str
    columns: list[ColumnInfo]
    sample_data: list[dict[str, Any]]
    row_count: int | None

    @property
    def full_name(self) -> str:
        return f"{self.schema_name}.{self.table_name}"


@dataclass
class Relationship:
    from_table: str
    from_column: str
    to_table: str
    to_column: str


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env: {name}")
    return value


def get_database_name() -> str:
    return require_env("SNOWFLAKE_DATABASE")


def connect():
    args: dict[str, Any] = {
        "user": require_env("SNOWFLAKE_USER"),
        "password": require_env("SNOWFLAKE_PASSWORD"),
        "account": require_env("SNOWFLAKE_ACCOUNT"),
        "database": get_database_name(),
    }

    return snowflake.connector.connect(**args)


def fetch_all(cur, sql: str):
    cur.execute(sql)
    return cur.fetchall()


def list_schemas(cur) -> list[str]:
    database_name = get_database_name().replace("'", "''")
    rows = fetch_all(
        cur,
        f"""
        SELECT SCHEMA_NAME
        FROM INFORMATION_SCHEMA.SCHEMATA
        WHERE CATALOG_NAME = '{database_name}'
          AND SCHEMA_NAME NOT IN ('INFORMATION_SCHEMA', 'PUBLIC')
        ORDER BY SCHEMA_NAME
        """,
    )
    return [r[0] for r in rows]


def list_tables(cur, schema_name: str) -> list[str]:
    escaped_schema = schema_name.replace("'", "''")
    rows = fetch_all(
        cur,
        f"""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = '{escaped_schema}'
          AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
        """,
    )
    return [r[0] for r in rows]


def describe_table(cur, schema_name: str, table_name: str) -> list[ColumnInfo]:
    cur.execute(f'DESCRIBE TABLE "{schema_name}"."{table_name}"')
    rows = cur.fetchall()
    return [
        ColumnInfo(name=row[0], dtype=row[1], nullable=(row[3] == "Y" if len(row) > 3 else True))
        for row in rows
    ]


def sample_rows(cur, schema_name: str, table_name: str, columns: list[str], limit: int = 2) -> list[dict[str, Any]]:
    if not columns:
        return []

    quoted_cols = ", ".join(f'"{c}"' for c in columns[:20])
    cur.execute(f'SELECT {quoted_cols} FROM "{schema_name}"."{table_name}" LIMIT {limit}')

    samples = []
    for row in cur.fetchall():
        row_dict = {}
        for idx, col in enumerate(columns[:20]):
            value = row[idx]
            if isinstance(value, (bytes, bytearray)):
                value = "<BINARY>"
            elif isinstance(value, str) and len(value) > 80:
                value = value[:77] + "..."
            elif isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, date):
                value = value.isoformat()
            elif isinstance(value, Decimal):
                value = float(value)
            row_dict[col] = value
        samples.append(row_dict)
    return samples


def row_count(cur, schema_name: str, table_name: str) -> int | None:
    try:
        cur.execute(f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"')
        return int(cur.fetchone()[0])
    except Exception:
        return None


def load_tables() -> list[TableInfo]:
    with connect() as conn:
        cur = conn.cursor()
        try:
            tables: list[TableInfo] = []
            for schema_name in list_schemas(cur):
                print(f"Processing schema: {schema_name}")
                for table_name in list_tables(cur, schema_name):
                    try:
                        columns = describe_table(cur, schema_name, table_name)
                    except Exception as exc:
                        print(f"  Skip {schema_name}.{table_name}: {exc}")
                        continue

                    col_names = [c.name for c in columns]
                    samples = sample_rows(cur, schema_name, table_name, col_names)
                    count = row_count(cur, schema_name, table_name)

                    tables.append(
                        TableInfo(
                            schema_name=schema_name,
                            table_name=table_name,
                            columns=columns,
                            sample_data=samples,
                            row_count=count,
                        )
                    )
                    print(f"  OK {table_name}: {len(columns)} cols, {count if count is not None else '?'} rows")

            return tables
        finally:
            cur.close()


def infer_relationships(tables: list[TableInfo]) -> list[dict[str, str]]:
    by_column: dict[str, list[TableInfo]] = {}
    for table in tables:
        for col in table.columns:
            by_column.setdefault(col.name.lower(), []).append(table)

    relationships: list[Relationship] = []

    for table in tables:
        for col in table.columns:
            col_name = col.name.lower()
            if not col_name.endswith("_id"):
                continue

            candidates = [t for t in by_column.get(col_name, []) if t.full_name != table.full_name]
            if not candidates:
                continue

            chosen = choose_target_table(source=table, fk_column=col_name, candidates=candidates)
            if not chosen:
                continue

            relationships.append(
                Relationship(
                    from_table=table.full_name,
                    from_column=col.name,
                    to_table=chosen.full_name,
                    to_column=col.name,
                )
            )

    dedup = {
        (r.from_table, r.from_column, r.to_table, r.to_column): r for r in relationships
    }
    return [
        {
            "from_table": rel.from_table,
            "from_column": rel.from_column,
            "to_table": rel.to_table,
            "to_column": rel.to_column,
        }
        for rel in dedup.values()
    ]


def choose_target_table(source: TableInfo, fk_column: str, candidates: list[TableInfo]) -> TableInfo | None:
    base = fk_column[:-3]  # remove '_id'

    best_score = -10**9
    best_table: TableInfo | None = None

    for candidate in candidates:
        score = 0

        # Prefer same schema.
        if candidate.schema_name == source.schema_name:
            score += 3

        # Prefer table names matching fk stem (user_id -> users/user).
        cand = candidate.table_name.lower()
        if cand == base or cand == base + "s" or cand.endswith("_" + base) or cand.endswith("_" + base + "s"):
            score += 4
        elif base in cand:
            score += 1

        # Prefer smaller table as potential dimension/reference table.
        if candidate.row_count is not None and source.row_count is not None:
            if candidate.row_count <= source.row_count:
                score += 1

        if score > best_score:
            best_score = score
            best_table = candidate

    return best_table


def save_schema_file(tables: list[TableInfo], relationships: list[dict[str, str]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    for filename in ("full_schema.json", "schema_compact.txt", "schema_reference.md"):
        obsolete = out_dir / filename
        if obsolete.exists():
            obsolete.unlink()

    database_name = get_database_name()
    detailed_lines = [
        f"# {database_name} Database Schema",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"# Tables: {len(tables)}",
        "",
    ]

    for t in sorted(tables, key=lambda x: (x.schema_name, x.table_name)):
        detailed_lines.append(f"## {t.full_name}")
        if t.row_count is not None:
            detailed_lines.append(f"# Rows: {t.row_count:,}")
        for c in t.columns:
            detailed_lines.append(f"  {c.name} {c.dtype} {'NULL' if c.nullable else 'NOT NULL'}")
        if t.sample_data:
            detailed_lines.append("")
            detailed_lines.append("  # Sample data:")
            for idx, row in enumerate(t.sample_data[:2], 1):
                sample = ", ".join(f"{k}={v}" for k, v in list(row.items())[:5])
                detailed_lines.append(f"  # Row {idx}: {sample}")
        detailed_lines.append("")

    detailed_lines.append("## Relationships")
    for rel in relationships:
        detailed_lines.append(
            f"  {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}"
        )
    detailed_lines.append("")

    (out_dir / "schema.txt").write_text("\n".join(detailed_lines), encoding="utf-8")


def ensure_rules_file(out_dir: Path) -> None:
    rules_file = out_dir / "rules.json"
    if rules_file.exists():
        return

    rules = {
        "schema_selection": {
            "instruction": "You are a database schema selection expert.\n\nSelect only the tables and columns needed to answer the question.",
            "join_hints": [
                "For ID joins, check data types and CAST when needed.",
                "Prefer joining *_id columns to corresponding reference tables.",
                "Avoid joining human-readable name fields when stable keys exist.",
            ],
            "timestamp_hints": [
                "Verify timestamp unit (seconds, milliseconds, or microseconds) before conversion.",
                "Use TO_TIMESTAMP after normalizing timestamp units.",
            ],
            "response_format": (
                "Return JSON only:\n"
                '{\n'
                '  "selected_tables": [\n'
                '    {"schema_name": "SCHEMA", "table_name": "TABLE", "columns": ["col_a", "col_b"]}\n'
                '  ],\n'
                '  "reasoning": "short reasoning"\n'
                '}'
            ),
        },
        "sql_generation": {
            "instruction": "You are a Snowflake SQL expert.\n\nGenerate a correct SQL query for the user question.",
            "rules": [
                "Quote Snowflake column names with double quotes when case-sensitive.",
                "Use only tables/columns from the provided schema string.",
                "Prefer explicit JOIN predicates and stable aliases.",
                "Keep SQL read-only.",
                "Add LIMIT for large result sets when user did not specify one.",
                "Use Snowflake-compatible syntax.",
            ],
            "quoting_instruction": (
                "All column names in this database are case-sensitive and defined "
                "with double-quoted lowercase identifiers.\n"
                'You MUST wrap every column reference in double quotes, '
                'for example: SELECT "column_name" FROM ...\n'
                "Table/schema names should NOT be quoted (they are uppercase and case-insensitive)."
            ),
            "response_format": "Output SQL only. Use markdown SQL fence.",
        },
    }
    rules_file.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    print("Generating schema metadata from Snowflake...")
    tables = load_tables()
    relationships = infer_relationships(tables)

    out_dir = Path("schema")
    save_schema_file(tables, relationships, out_dir)
    ensure_rules_file(out_dir)

    print(f"Done. tables={len(tables)} relationships={len(relationships)}")


if __name__ == "__main__":
    main()
