from __future__ import annotations

import argparse
import asyncio
import json

from spatialmas.agent import ChatAgent
from spatialmas.langchain_tools import (
    analyze_query_result,
    execute_db_query,
    generate_sql_query,
    select_relevant_schema,
)


async def run(prompt: str) -> None:
    agent = ChatAgent(
        tools=[
            select_relevant_schema,
            generate_sql_query,
            execute_db_query,
            analyze_query_result,
        ],
        system_message=(
            "You are a data research assistant. "
            "Use tools in order: select_relevant_schema -> generate_sql_query -> execute_db_query."
        ),
    )

    print(f"[USER] {prompt}\n")
    print("[ASSISTANT] ", end="", flush=True)

    async for chunk in agent.chat_stream(prompt):
        chunk_type = chunk.get("type")
        if chunk_type == "content":
            print(chunk["data"], end="", flush=True)
        elif chunk_type == "tool_start":
            print(f"\n\n[TOOL START] {chunk['name']}")
            print(json.dumps(chunk["input"], ensure_ascii=False, indent=2))
        elif chunk_type == "tool_end":
            print(f"\n[TOOL END] {chunk['name']}")
            output = chunk.get("output")
            if isinstance(output, str):
                print(output[:1200])
            else:
                print(output)

    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="SpatialMAS local CLI")
    parser.add_argument("prompt", nargs="?", default="Show a sample summary from available tables")
    args = parser.parse_args()
    asyncio.run(run(args.prompt))


if __name__ == "__main__":
    main()
