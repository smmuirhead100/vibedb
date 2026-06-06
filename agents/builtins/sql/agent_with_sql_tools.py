import os
from typing import Optional, Self

from agents.builtins.sql.schemas import AgentWithSQLToolsOptions, AgentWithSQLToolsPermissions
from agents.builtins.sql.services import DatabaseService
from agents.core.agent_with_tools import AgentWithTools
from agents.core.tools import tool
from llms.gemini.models import GeminiLLMModel
from llms.gemini.llm import LLM as GeminiLLM


PROMPT_TEMPLATE = open(os.path.join(os.path.dirname(__file__), "prompt_template.md"), "r").read()


def _default_llm() -> GeminiLLM:
    return GeminiLLM(model=GeminiLLMModel.GEMINI_3_FLASH_PREVIEW)


def _default_options() -> AgentWithSQLToolsOptions:
    return AgentWithSQLToolsOptions(
        database_url=os.getenv("DATABASE_URL"),
        permissions=AgentWithSQLToolsPermissions(),
    )


async def _build_instructions(options: AgentWithSQLToolsOptions, db_service: DatabaseService) -> str:
    return PROMPT_TEMPLATE.format(
        create=options.permissions.create,
        read=options.permissions.read,
        update=options.permissions.update,
        delete=options.permissions.delete,
        database_overview=await db_service.list_tables(),
    )


class AgentWithSQLTools(AgentWithTools):
    def __init__(
        self,
        instructions: str,
        db_service: DatabaseService,
        options: AgentWithSQLToolsOptions,
    ) -> None:
        self.options = options
        self.db_service = db_service
        super().__init__(llm=_default_llm(), instructions=instructions)

    @classmethod
    async def create(cls, database_url: str) -> Self:
        db_service = DatabaseService(db_url=database_url)
        options = AgentWithSQLToolsOptions(permissions=AgentWithSQLToolsPermissions())
        instructions = await _build_instructions(options, db_service)
        return cls(instructions=instructions, db_service=db_service, options=options)

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
    async def list_tables(self) -> str:
        """
        List all tables in the database.

        Returns:
            A formatted string listing all table names in the database
        """
        return await self.db_service.list_tables()

    @tool
    async def list_schemas(self) -> str:
        """
        List all schemas in the database.

        Returns:
            A formatted string listing all schema names
        """
        return await self.db_service.list_schemas()

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
