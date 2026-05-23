# SpatialMAS

SpatialMAS is a standalone MCP server for spatial and tabular analytics workflows.

It focuses on:

- secure configuration (env-based)
- read-only SQL execution
- structured JSON tool outputs
- modular architecture for long-term maintenance

## MCP tools

1. `select_relevant_schema`
2. `generate_sql_query`
3. `execute_db_query`
4. `analyze_query_result`

## Project structure

```text
SpatialMAS/                      ← repo root
├── mcp_server.py                ← MCP server entry
├── main.py                      ← CLI demo entry
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
- `SNOWFLAKE_DATABASE`

Optional:

- `SNOWFLAKE_WAREHOUSE`
- `SNOWFLAKE_ROLE`
- `QUERY_TIMEOUT_SECONDS` (default `30`)
- `DEFAULT_RESULT_LIMIT` (default `1000`)
- `MAX_RESULT_LIMIT` (default `5000`)

## Run

### MCP server

```bash
python mcp_server.py
```

### Local CLI demo

```bash
python main.py "Show top 10 records from the main fact table"
```

### Rebuild the LLM schema from your own database

```bash
python scripts/generate_schema.py
python scripts/validate_schema.py
```

## Notes

- This repository ships with a single LLM-facing schema file.
- Run `scripts/generate_schema.py` to regenerate the schema file and rules for your own environment.
- The server rejects non-read-only SQL.
