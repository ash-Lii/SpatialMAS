# SpatialMAS

SpatialMAS is a standalone CLI for spatial and tabular analytics workflows.

It focuses on:

- env-based configuration
- read-only SQL execution
- structured outputs
- modular architecture for long-term maintenance

## Core tool pipeline

1. `select_relevant_schema`
2. `generate_sql_query`
3. `execute_db_query`
4. `analyze_query_result`

## Project structure

```text
SpatialMAS/                      ← repo root
├── db.py                        ← direct SQL runner
├── questions.md                 ← batch questions for main.py
├── test.py                      ← batch runner that streams stdout and writes answers/
├── answers/                     ← generated per-question answer files with logs
├── main.py                      ← CLI entry
├── pyproject.toml
├── .env.example
├── spatialmas/                  ← Python package
│   ├── config.py
│   ├── models.py
│   ├── agent.py
│   ├── langchain_tools.py
│   ├── infra/
│   │   ├── llm_client.py
│   │   └── snowflake_client.py
│   ├── schema/
│   │   └── loader.py
│   └── services/
│       ├── schema_service.py
│       ├── sql_service.py
│       ├── query_service.py
│       └── analysis_service.py
├── schema/                      ← LLM schema + rules
│   ├── schema.txt
│   └── rules.json
├── scripts/                     ← one-off utilities
│   ├── generate_schema.py
│   └── validate_schema.py
└── tests/                       ← test suite
    ├── test_sql_guard.py
    └── test_schema_relationships.py
```

## Environment

Create `.env` from `.env.example`.

Required:

- `OPENAI_API_KEY`
- `OPENAI_API_BASE`
- `MODEL`
- `SNOWFLAKE_USER`
- `SNOWFLAKE_PASSWORD`
- `SNOWFLAKE_ACCOUNT`

Optional:

- `SNOWFLAKE_DATABASE` (default `SAN_FRANCISCO_PLUS`)
- `QUERY_TIMEOUT_SECONDS` (default `30`)
- `DEFAULT_RESULT_LIMIT` (default `1000`)
- `MAX_RESULT_LIMIT` (default `5000`)

## Run

Natural language / agent flow:

```bash
python main.py "Show top 10 records from the main fact table"
```

Direct SQL:

```bash
python db.py "SELECT * FROM SAN_FRANCISCO_BIKESHARE.BIKESHARE_TRIPS LIMIT 10"
```

Both commands use the same `.env`-based Snowflake settings, and `db.py` keeps the existing read-only guard.

Batch evaluation:

```bash
python test.py
```

`test.py` reads questions from `questions.md`, streams `main.py` stdout to the console while it runs, and overwrites `answers/` with one Markdown file per question, including the full run logs.

## Schema utilities

```bash
python scripts/generate_schema.py
python scripts/validate_schema.py
```

## Notes

- This repository is CLI-only; no separate server registration is required.
- Run `scripts/generate_schema.py` to regenerate the schema file and rules for your own environment.
- `test.py` is a batch harness; it does not replace `db.py` or `main.py`.
- The command entry points enforce read-only SQL.
