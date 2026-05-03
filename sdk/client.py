from agents.builtins.sql.agent_with_sql_tools import AgentWithSQLTools
from agents.core.chat_context import ChatMessage, ChatRole
from agents.core.tools import ToolCall


class Client:
    def __init__(self) -> None:
        self._agent = AgentWithSQLTools()

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
