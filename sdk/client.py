import os
from typing import Optional
from agents.builtins.sql.agent_with_sql_tools import AgentWithSQLTools
from agents.core.chat_context import ChatMessage, ChatRole
from agents.core.tools import ToolCall

import logging
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        RichHandler(
            rich_tracebacks=True,
            show_path=False,
        )
    ],
)


class Client:
    def __init__(self, database_url: Optional[str] = None) -> None:
        database_url = database_url or os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set or provided")
        self._agent = AgentWithSQLTools(database_url=database_url)

    async def execute(self, query: str) -> str:
        """Execute an arbitrary query against the database."""
        response = ""
        async for chunk in self._agent.astream(chat_message=ChatMessage(role=ChatRole.USER, content=query)):
            if isinstance(chunk, ToolCall):
                continue
            response += chunk
        return response

    async def create(self, query: str) -> str:
        """Create a new record in the database."""
        response = ""
        async for chunk in self._agent.astream(chat_message=ChatMessage(role=ChatRole.USER, content=query)):
            if isinstance(chunk, ToolCall):
                continue
            response += chunk
        return response

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
