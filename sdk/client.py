from agents.builtins.agent_with_sql_tools import AgentWithSQLTools
from agents.core.chat_context import ChatMessage, ChatRole
from agents.core.tools import ToolCall


class Client:
    def __init__(self, database_url: str) -> None:
        self.db_url = database_url
        self._agent = AgentWithSQLTools(
            database_url=database_url,
        )

    async def execute(self, query: str) -> str:
        response = ""
        async for chunk in self._agent.astream(chat_message=ChatMessage(role=ChatRole.USER, content=query)):
            if isinstance(chunk, ToolCall):
                continue
            response += chunk
        return response
