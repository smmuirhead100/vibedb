import os
from typing import AsyncGenerator

from anthropic import AsyncAnthropic
from .models import AnthropicLLMModel
from llms.llm import LLM as BaseLLM


class LLM(BaseLLM):
    def __init__(self, model: AnthropicLLMModel = AnthropicLLMModel.CLAUDE_4_5_SONNET) -> None:
        self.model = model
        self.client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    async def astream(self, prompt: str) -> AsyncGenerator[str]:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                agents={
                    "agent": AgentDefinition(tools=self.tools),
                },
            ),
        ):
            yield message.content