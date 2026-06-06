import os
from typing import Self

from agents.builtins.sql.schemas import AgentWithSQLToolsOptions, AgentWithSQLToolsPermissions
from sdk.query_cache import QueryCache
from agents.core.agent_with_tools import AgentWithTools
from agents.core.tools import tool
from llms.gemini.models import GeminiLLMModel
from llms.gemini.llm import LLM as GeminiLLM
from sdk.database_service import DatabaseService


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

    @tool
    async def execute_query(self, query: str) -> str:
        """
        Execute a SQL query against the database and return the results.
        Use this for SELECT queries to retrieve data, or for DDL/DML operations.

        Args:
            query: The SQL query to execute (SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, etc.)

        Returns:
            A string
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
        self.query_cache.add_query_to_cache(natural_language_template, sql_template)
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
