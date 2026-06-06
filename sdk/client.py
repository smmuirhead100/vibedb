import os
from typing import Optional, Self
from agents.builtins.sql.agent_with_sql_tools import AgentWithSQLTools
from agents.builtins.sql.schemas import AgentWithSQLToolsOptions
from agents.core.chat_context import ChatMessage, ChatRole
from agents.core.tools import ToolCall

import logging
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    handlers=[
        RichHandler(
            rich_tracebacks=True,
            show_path=False,
        )
    ],
)

logger = logging.getLogger(__name__)


class Client:
    def __init__(self, agent: AgentWithSQLTools) -> None:
        self._agent = agent

    @classmethod
    async def create(cls, database_url: str) -> Self:
        agent = await AgentWithSQLTools.create(database_url=database_url)
        return cls(agent=agent)

    async def execute(self, query: str) -> str:
        """Execute an arbitrary query against the database."""
        response = ""
        async for chunk in self._agent.astream(chat_message=ChatMessage(role=ChatRole.USER, content=query)):
            if isinstance(chunk, ToolCall):
                logger.info(f"Tool call: {chunk.name}({chunk.args}) -> {chunk.response}")
                continue
            logger.info(f"Chunk: {chunk}")
            response += chunk
        return response

    # async def create(self, query: str) -> str:
    #     """Create a new record in the database."""
    #     response = ""
    #     async for chunk in self._agent.astream(chat_message=ChatMessage(role=ChatRole.USER, content=query)):
    #         if isinstance(chunk, ToolCall):
    #             continue
    #         response += chunk
    #     return response

    async def get(self, query: str) -> str:
        """Get a record from the database."""
        response = ""
        async for chunk in self._agent.astream(chat_message=ChatMessage(role=ChatRole.USER, content=query)):
            if isinstance(chunk, ToolCall):
                continue
            response += chunk
        return response

    async def update(self, query: str) -> str:
        """Update a record in the database."""
        response = ""
        async for chunk in self._agent.astream(chat_message=ChatMessage(role=ChatRole.USER, content=query)):
            if isinstance(chunk, ToolCall):
                continue
            response += chunk
        return response

    async def delete(self, query: str) -> str:
        """Delete a record from the database."""
        response = ""
        async for chunk in self._agent.astream(chat_message=ChatMessage(role=ChatRole.USER, content=query)):
            if isinstance(chunk, ToolCall):
                continue
            response += chunk
        return response
