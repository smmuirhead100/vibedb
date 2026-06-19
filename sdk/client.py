import logging
from typing import Any, List, Self, Type

from pydantic import BaseModel
from rich.logging import RichHandler

from agents.builtins.sql.agent_with_sql_tools import AgentWithSQLTools
from sdk.casting import cast_result
from sdk.handler_runtime import make_executor, run_handler
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

    async def execute(self, query: str, return_as: Type[BaseModel] | Type[list[BaseModel]] | None = None) -> BaseModel | List[BaseModel]:
        """Execute an arbitrary query against the database."""
        # 1. Check if the query is in cache.
        cached_query = self._query_cache.get_cached_query(query)
        if cached_query:
            handler_source, params = cached_query
            executor = make_executor(self._db_service)
            result = await run_handler(handler_source, executor, params)
            return cast_result(result, return_as)

        # 2. Otherwise use the agent to execute the query.
        return await self._agent.execute(query=query, return_as=return_as)

    async def dispose(self) -> None:
        await self._db_service.dispose()
