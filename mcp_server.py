"""SpatialMAS MCP server."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from spatialmas.models import QueryExecutionError
from spatialmas.services.analysis_service import AnalysisService
from spatialmas.services.query_service import QueryService
from spatialmas.services.schema_service import SchemaSelectionService
from spatialmas.services.sql_service import SQLGenerationService


server = Server("SpatialMAS")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="select_relevant_schema",
            description="Select relevant tables/columns for a natural-language analytics question.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "User question"},
                },
                "required": ["question"],
            },
        ),
        Tool(
            name="generate_sql_query",
            description="Generate Snowflake SQL using question + simplified schema.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "schema_string": {"type": "string"},
                },
                "required": ["question", "schema_string"],
            },
        ),
        Tool(
            name="execute_db_query",
            description="Execute read-only SQL and return structured JSON results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql_query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 5000},
                },
                "required": ["sql_query"],
            },
        ),
        Tool(
            name="analyze_query_result",
            description="Analyze query result rows (JSON array) and return statistical insights.",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "JSON array rows"},
                    "analysis_type": {
                        "type": "string",
                        "enum": ["basic", "statistical", "trend", "comprehensive"],
                        "default": "comprehensive",
                    },
                },
                "required": ["data"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "select_relevant_schema":
            service = SchemaSelectionService()
            result = service.select_relevant_schema(question=arguments["question"])
            return [_text(result.to_dict())]

        if name == "generate_sql_query":
            service = SQLGenerationService()
            sql = service.generate_sql(
                question=arguments["question"],
                schema_string=arguments["schema_string"],
            )
            return [_text({"sql": sql})]

        if name == "execute_db_query":
            service = QueryService()
            result = service.execute_query(
                sql_query=arguments["sql_query"],
                limit=arguments.get("limit"),
            )
            return [_text(result.to_dict())]

        if name == "analyze_query_result":
            service = AnalysisService()
            result = service.analyze_query_result(
                data=arguments["data"],
                analysis_type=arguments.get("analysis_type", "comprehensive"),
            )
            return [_text(result)]

        return [_text(QueryExecutionError(code="UNKNOWN_TOOL", message=f"Unknown tool: {name}").to_dict())]

    except Exception as exc:
        error = QueryExecutionError(
            code="TOOL_EXECUTION_ERROR",
            message=str(exc),
            details={"tool": name},
        )
        return [_text(error.to_dict())]


def _text(payload: dict[str, Any]) -> TextContent:
    return TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, indent=2))


async def run_server() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
