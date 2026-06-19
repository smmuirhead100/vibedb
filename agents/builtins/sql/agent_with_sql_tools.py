import os
from typing import Optional, Self, Type

from pydantic import BaseModel

from agents.builtins.sql.schemas import AgentWithSQLToolsOptions, AgentWithSQLToolsPermissions
from agents.core.chat_context import ChatMessage, ChatRole
from sdk.query_cache import QueryCache
from agents.core.agent_with_tools import AgentWithTools
from agents.core.tools import ToolCall, tool
from llms.gemini.models import GeminiLLMModel
from llms.gemini.llm import LLM as GeminiLLM
from sdk.database_service import DatabaseService, ExecuteQueryResult
import logging

logger = logging.getLogger(__name__)


PROMPT_TEMPLATE = open(os.path.join(os.path.dirname(__file__), "prompt_template.md"), "r").read()


def _default_llm() -> GeminiLLM:
    return GeminiLLM(model=GeminiLLMModel.GEMINI_3_FLASH_PREVIEW)


async def _build_instructions(options: AgentWithSQLToolsOptions, db_service: DatabaseService) -> str:
    return PROMPT_TEMPLATE.format(
        create=options.permissions.create,
        read=options.permissions.read,
        update=options.permissions.update,
        delete=options.permissions.delete,
        database_overview=await db_service.get_overview_of_database(),
    )


class AgentWithSQLTools(AgentWithTools):
    def __init__(
        self,
        instructions: str,
        db_service: DatabaseService,
        query_cache: QueryCache,
        options: AgentWithSQLToolsOptions,
    ) -> None:
        self.options = options
        self.db_service = db_service
        self.query_cache = query_cache
        super().__init__(llm=_default_llm(), instructions=instructions)

    @classmethod
    async def create(
        cls,
        db_service: DatabaseService,
        query_cache: QueryCache,
        options: AgentWithSQLToolsOptions | None = None,
    ) -> Self:
        options = options or AgentWithSQLToolsOptions(permissions=AgentWithSQLToolsPermissions())
        instructions = await _build_instructions(options, db_service)
        return cls(
            instructions=instructions,
            db_service=db_service,
            query_cache=query_cache,
            options=options,
        )

    async def execute(self, query: str, return_as: Type[BaseModel] | None = None) -> Optional[BaseModel]:
        """Execute a SQL query against the database and return the results."""
        cached_query = self.query_cache.get_cached_query(query)
        if cached_query:
            resolved_sql, _ = cached_query
            response = await self.db_service.execute_query(resolved_sql)
        else:
            response = ""
            # TODO: For large queries, we're gonna need to let the LLM write a script or something. It can't just output everything manually.
            # Something like this maybe? execute_query(query: str, lambda: Callable[[str], ExecuteQueryResult])
            async for chunk in self.astream(chat_message=ChatMessage(role=ChatRole.USER, content=query)):
                if isinstance(chunk, ToolCall):
                    logger.info(f"TOOL CALL: {chunk.name}({chunk.args}) -> {chunk.response}")
                    continue
                response += chunk
        if return_as:
            return return_as.model_validate_json(response.model_dump_json())
        return None
    
    @tool
    async def execute_query(self, query: str) -> ExecuteQueryResult:
        """
        Execute a SQL query against the database and return the results.
        Use this for SELECT queries to retrieve data, or for DDL/DML operations.

        Args:
            query: The SQL query to execute (SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, etc.)

        Returns:
            An ExecuteQueryResult object. Here is the rough implementation of this method under the hood:
                ```
                class ExecuteQueryRowValueResult(BaseModel):
                    column: str
                    value: Any


                class ExecuteQueryRowResult(BaseModel):
                    values: list[ExecuteQueryRowValueResult]


                class ExecuteQueryResult(BaseModel):
                    rows: list[ExecuteQueryRowResult]


                async def execute_query(self, query: str) -> ExecuteQueryResult:
                    try:
                        async with self.engine.begin() as connection:
                            result = await connection.execute(text(query))

                            if result.returns_rows:
                                rows = result.fetchall()
                                columns = result.keys()

                                if not rows:
                                    return ExecuteQueryResult(rows=[])

                                return ExecuteQueryResult(rows=[ExecuteQueryRowResult(
                                    values=[
                                        ExecuteQueryRowValueResult(column=col, value=val)
                                        for col, val in zip(columns, row)
                                        if val is not None
                                    ]
                                ) for row in rows])
                            return ExecuteQueryResult(rows=[])
                    except SQLAlchemyError as e:
                        raise Exception(f"Error executing query: {str(e)}")
                    except Exception as e:
                        raise Exception(f"Unexpected error: {str(e)}")
                ```
        """
        return await self.db_service.execute_query(query)

    @tool
    async def cache_query(self, natural_language_template: str, sql_template: str) -> str:
        """
        Cache a query pattern so similar future requests can skip LLM reasoning and run directly.

        Use placeholders in curly braces for variable parts that appear in both templates.
        After executing a query successfully, cache it when the same kind of request is likely
        to come up again.

        Args:
            natural_language_template: Natural language pattern with placeholders, e.g.
                "New Event: new user signed up with first name {first_name} and last name {last_name}. Phone number is {phone}."
            sql_template: The SQL to run with the same placeholders, e.g.
                "INSERT INTO users (first_name, last_name, phone) VALUES ('{first_name}', '{last_name}', '{phone}')"

        Returns:
            A confirmation message
        """
        self.query_cache.add(natural_language_template, sql_template)
        return "Query cached successfully."

    @tool
    async def throw_error(self, error: str) -> str:
        """
        Throw an error.

        Args:
            error: The error to throw

        Returns:
            A string
        """
        raise Exception(error)
