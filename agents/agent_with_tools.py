from typing import AsyncGenerator
from agents.tools import Tool


class AgentWithTools:
    def __init__(self, tools: list[Tool]) -> None:
        self.tools = tools

    def astream(self, prompt: str) -> AsyncGenerator[str]:
        
        
