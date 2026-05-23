# SpatialMAS Deployment Notes

## Compatibility

Core tool names:

- `select_relevant_schema`
- `generate_sql_query`
- `execute_db_query`
- `analyze_query_result`

## Key behaviors

1. Env-based configuration only.
2. Structured JSON outputs.
3. Read-only SQL enforcement.

## Setup checklist

1. Copy `.env.example` to `.env` and fill values.
2. Register `SpatialMAS/mcp_server.py` in your MCP client.
3. Run smoke tests and schema validation.
