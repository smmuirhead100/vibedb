import json
import os
from typing import Any, Dict, List, Optional, Self, Type, get_args, get_origin

from pydantic import BaseModel

from agents.builtins.sql.schemas import AgentWithSQLToolsOptions, AgentWithSQLToolsPermissions
from agents.core.chat_context import ChatMessage, ChatRole
from sdk.query_cache import QueryCache
from agents.core.agent_with_tools import AgentWithTools
from agents.core.tools import ToolCall, tool
from sdk.casting import cast_result as cast_result_to_type
from llms.gemini.models import GeminiLLMModel
from llms.gemini.llm import LLM as GeminiLLM
from sdk.database_service import DatabaseService, ExecuteQueryResult
import logging

logger = logging.getLogger(__name__)

CAST_RESULT_TOOL_NAME = "cast_result"


PROMPT_TEMPLATE = open(os.path.join(os.path.dirname(__file__), "prompt_template.md"), "r").read()


def _default_llm() -> GeminiLLM:
    return GeminiLLM(model=GeminiLLMModel.GEMINI_3_FLASH_PREVIEW)


def _describe_target_schema(return_as: Type[Any]) -> str | None:
    """Render return_as as an instruction so the LLM knows the target shape to cast to.

    The application schema may differ from the database schema (e.g. a `phone` field
    backed by a `phone_number` column), so the LLM must see the target field names to
    transform DB rows into it. Returns None if return_as isn't a model we can describe.
    """
    origin = get_origin(return_as)
    if origin is list:
        args = get_args(return_as)
        item = args[0] if args else None
        if isinstance(item, type) and issubclass(item, BaseModel):
            schema = json.dumps(item.model_json_schema())
            return (
                f"Return the result by calling {CAST_RESULT_TOOL_NAME} with a JSON array of "
                f"objects matching this schema (transform DB columns to these exact field "
                f"names):\n{schema}"
            )
        return None
    if isinstance(return_as, type) and issubclass(return_as, BaseModel):
        schema = json.dumps(return_as.model_json_schema())
        return (
            f"Return the result by calling {CAST_RESULT_TOOL_NAME} with a JSON object "
            f"matching this schema (transform DB columns to these exact field names):\n{schema}"
        )
    return None


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
        # TODO: For large queries, we're gonna need to let the LLM write a script or something. It can't just output everything manually.
        # Something like this maybe? execute_query(query: str, lambda: Callable[[str], ExecuteQueryResult])
        content = query
        if return_as is not None:
            schema_hint = _describe_target_schema(return_as)
            if schema_hint is not None:
                content = f"{query}\n\n{schema_hint}"

        response = ""
        async for chunk in self.astream(chat_message=ChatMessage(role=ChatRole.USER, content=content)):
            if isinstance(chunk, ToolCall):
                logger.info(f"TOOL CALL: {chunk.name}({chunk.args}) -> {chunk.response}")

                # Hacks: Handle the cast_result tool call.
                if chunk.name == CAST_RESULT_TOOL_NAME:
                    # Use args (the structured data the LLM passed) rather than the
                    # stringified response.
                    data = (chunk.args or {}).get("result")
                    return self._cast_result(result=data, return_as=return_as)

                continue
            response += chunk

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
    async def cache_query(self, natural_language_template: str, handler_source: str) -> str:
        """
        Cache a query handler so similar future requests can skip LLM reasoning and run directly.

        After handling a request successfully, cache it when the same kind of request is likely
        to recur. The handler you provide should reproduce BOTH the query you ran and the
        transformation you applied in cast_result, so the cached path returns the same shape.

        Args:
            natural_language_template: Natural language pattern with `{placeholder}` slots for the
                parts that change, e.g. "Get user with id {id}". Keep fixed wording identical to
                what you expect in future messages.
            handler_source: Source code for an async function named `handler` with the signature
                `async def handler(execute_query, params)`:
                  - `execute_query(sql, params)` runs SQL with bind params and returns a list of
                    row dicts. Use `:name` bind parameters — never string-format values into SQL.
                  - `params` is a dict of the values extracted from the message, keyed by the same
                    names as the `{placeholder}` slots in natural_language_template.
                  - Return model-shaped dicts (a single dict or a list), applying the same field
                    transformation you did in cast_result.
                Example:
                  "async def handler(execute_query, params):\\n"
                  "    rows = await execute_query('SELECT * FROM users WHERE id = :id', params)\\n"
                  "    return [{'id': r['id'], 'phone': r['phone_number']} for r in rows]"

        Returns:
            A confirmation message
        """
        self.query_cache.add(natural_language_template, handler_source)
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
        # TODO: Obviously need some deterministic way to prevent permission violations.
        raise Exception(error)

    @tool
    async def cast_result(self, result: Any) -> Any:
        """
        Cast the result of a query to a Pydantic model.
        """
        return result

    def _cast_result(self, result: Any, return_as: Type[BaseModel] | Type[List[Any]] | None) -> BaseModel | List[Any]:
        return cast_result_to_type(result, return_as)