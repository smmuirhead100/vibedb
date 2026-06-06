import logging
from typing import Self

from rich.logging import RichHandler

from agents.builtins.sql.agent_with_sql_tools import AgentWithSQLTools
from sdk.query_cache import QueryCache
from agents.core.chat_context import ChatMessage, ChatRole
from agents.core.tools import ToolCall
from sdk.database_service import DatabaseService

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

logger = logging.getLogger(__name__)


class Client:
    def __init__(
        self,
        agent: AgentWithSQLTools,
        db_service: DatabaseService,
        query_cache: QueryCache,
    ) -> None:
        self._agent = agent
        self._db_service = db_service
        self._query_cache = query_cache

    @classmethod
    async def create(cls, database_url: str) -> Self:
        db_service = DatabaseService(db_url=database_url)
        query_cache = QueryCache()
        agent = await AgentWithSQLTools.create(db_service=db_service, query_cache=query_cache)
        return cls(agent=agent, db_service=db_service, query_cache=query_cache)

    async def execute(self, query: str) -> str:
        """Execute an arbitrary query against the database."""
        cached_query = self._query_cache.get_cached_query(query)
        if cached_query:
            resolved_sql, _ = cached_query
            logger.info(f"Cached query: {query} -> {resolved_sql}")
            return await self._db_service.execute_query(resolved_sql)

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

    async def dispose(self) -> None:
        await self._db_service.dispose()
