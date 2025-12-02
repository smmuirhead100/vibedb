from typing import AsyncGenerator

from pydantic import BaseModel, ConfigDict
from agents.chat_context import ChatMessage
from agents.tools import Tool, ToolCall
from llms.llm import LLM


class AgentWithToolsOptions(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    llm: LLM
    tools: list[Tool]


class AgentWithTools:
    def __init__(self, options: AgentWithToolsOptions) -> None:
        self.options = options

    async def astream(self, messages: list[ChatMessage]) -> AsyncGenerator[str | ToolCall]:
        stream = self.options.llm.astream(
            messages=messages,
            tools=self.options.tools,
        )
        async for chunk in stream:
            if isinstance(chunk, ToolCall):
                tool_call_response = await self._execute_tool_call(tool_call=chunk)
                chunk.response = tool_call_response
            yield chunk

    async def _execute_tool_call(self, tool_call: ToolCall) -> str:
        method_name = tool_call.tool.name
        method = getattr(self, method_name)
        if not method:
            raise ValueError(f"Method '{method_name}' not found on {self.__class__.__name__}")
        result = await method(**tool_call.args)
        return str(result)
