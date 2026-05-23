from __future__ import annotations

import uuid
from typing import Callable

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from spatialmas.infra.llm_client import create_llm


class ChatAgent:
    def __init__(
        self,
        tools: list[Callable] | None = None,
        system_message: str = "You are a helpful data assistant.",
        temperature: float = 0,
    ) -> None:
        model = create_llm(temperature=temperature)
        self.agent = create_agent(
            model=model,
            tools=tools or [],
            system_prompt=system_message,
            checkpointer=InMemorySaver(),
        )
        self.thread_id = str(uuid.uuid4())

    async def chat_stream(self, message: str):
        async for event in self.agent.astream_events(
            {"messages": [{"role": "user", "content": message}]},
            config={"recursion_limit": 100, "configurable": {"thread_id": self.thread_id}},
            version="v1",
        ):
            kind = event.get("event", "")
            if kind == "on_tool_start":
                yield {
                    "type": "tool_start",
                    "name": event.get("name", "unknown"),
                    "input": event.get("data", {}).get("input", {}),
                }
            elif kind == "on_tool_end":
                output = event.get("data", {}).get("output")
                if hasattr(output, "content"):
                    output = output.content
                yield {
                    "type": "tool_end",
                    "name": event.get("name", "unknown"),
                    "output": output,
                }
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield {"type": "content", "data": chunk.content}

    def clear_history(self) -> None:
        self.thread_id = str(uuid.uuid4())
