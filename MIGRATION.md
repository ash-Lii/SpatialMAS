# SpatialMAS Deployment Notes

## Compatibility

SpatialMAS is now CLI-only. There is no separate server registration step.

Core tool names:

- `select_relevant_schema`
- `generate_sql_query`
- `execute_db_query`
- `analyze_query_result`

## Key behaviors

1. Env-based configuration only.
2. Structured outputs.
3. Read-only SQL enforcement.

## Setup checklist

1. Copy `.env.example` to `.env` and fill values.
2. Run `python main.py "Show a sample summary from available tables"`.
3. Run smoke tests and schema validation.
