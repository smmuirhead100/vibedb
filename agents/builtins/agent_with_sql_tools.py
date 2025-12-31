from sqlalchemy import create_engine, text, inspect as sql_inspect
from sqlalchemy.exc import SQLAlchemyError

from agents.core.agent_with_tools import AgentWithTools
from agents.core.tools import tool
from llms.gemini.models import GeminiLLMModel
from llms.gemini.llm import LLM

INSTRUCTIONS = """
# Identity
You are Bob, NaturalSQL's official Agent.

NaturalSQL is a database that changes the way users interact with a database by
allowing users to read and write to the database using natural language. You are
the primary point of contact for users who want to interact with the database.

You may receive queries, events, or any other form of raw data. Your job is to
maintain the database and ensure that it is always in a consistent state. This
will require you to run migrations, create indexes, and other database
maintenance tasks.

When executing SQL queries:
- Always use parameterized queries when possible to prevent SQL injection
- For SELECT queries, return the results in a clear, readable format
- For DDL operations (CREATE, ALTER, DROP), confirm the operation was successful
- If a query fails, provide a clear error message explaining what went wrong
"""


class AgentWithSQLTools(AgentWithTools):
    def __init__(self, database_url: str) -> None:
        llm = LLM(model=GeminiLLMModel.GEMINI_3_FLASH_PREVIEW)
        
        super().__init__(llm=llm, instructions=INSTRUCTIONS)
        
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.inspector = sql_inspect(self.engine)

    @tool
    async def execute_query(self, query: str) -> str:
        """
        Execute a SQL query against the database and return the results.
        Use this for SELECT queries to retrieve data, or for DDL/DML operations.

        Args:
            query: The SQL query to execute (SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, etc.)

        Returns:
            For SELECT queries: A formatted string with the query results
            For other queries: A confirmation message with the number of rows
            affected
        """
        try:
            with self.engine.begin() as connection:
                result = connection.execute(text(query))

                # Check if this is a SELECT query (has rows to return)
                if result.returns_rows:
                    rows = result.fetchall()
                    columns = result.keys()

                    if not rows:
                        return "Query executed successfully. No rows returned."

                    # Format results as a table
                    output_parts = []
                    # Header
                    header = " | ".join(str(col) for col in columns)
                    output_parts.append(header)
                    output_parts.append("-" * len(header))
                    # Rows
                    for row in rows:
                        row_str = " | ".join(
                            str(val) if val is not None else "NULL" for val in row
                        )
                        output_parts.append(row_str)

                    return "\n".join(output_parts)
                else:
                    # For INSERT, UPDATE, DELETE, DDL operations
                    # Transaction is automatically committed by 'begin()' context
                    rowcount = result.rowcount
                    return f"Query executed successfully. Rows affected: {rowcount}"

        except SQLAlchemyError as e:
            return f"Error executing query: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    @tool
    async def list_tables(self) -> str:
        """
        List all tables in the database.

        Returns:
            A formatted string listing all table names in the database
        """
        try:
            tables = self.inspector.get_table_names()
            if not tables:
                return "No tables found in the database."
            return "Tables in database:\n" + "\n".join(
                f"  - {table}" for table in tables
            )
        except Exception as e:
            return f"Error listing tables: {str(e)}"

    @tool
    async def describe_table(self, table_name: str) -> str:
        """
        Get detailed schema information about a specific table.

        Args:
            table_name: The name of the table to describe

        Returns:
            A formatted string with column names, types, and constraints
        """
        try:
            if not self.inspector.has_table(table_name):
                return f"Table '{table_name}' does not exist in the database."

            columns = self.inspector.get_columns(table_name)
            primary_keys = self.inspector.get_primary_keys(table_name)
            foreign_keys = self.inspector.get_foreign_keys(table_name)
            indexes = self.inspector.get_indexes(table_name)

            output_parts = [f"Schema for table '{table_name}':\n"]

            # Columns
            output_parts.append("Columns:")
            for col in columns:
                col_info = f"  - {col['name']}: {col['type']}"
                if col.get('nullable') is False:
                    col_info += " NOT NULL"
                if col.get('default') is not None:
                    col_info += f" DEFAULT {col['default']}"
                output_parts.append(col_info)

            # Primary keys
            if primary_keys:
                output_parts.append(
                    f"\nPrimary Keys: {', '.join(primary_keys)}"
                )

            # Foreign keys
            if foreign_keys:
                output_parts.append("\nForeign Keys:")
                for fk in foreign_keys:
                    fk_info = (
                        f"  - {fk['constrained_columns']} -> "
                        f"{fk['referred_table']}.{fk['referred_columns']}"
                    )
                    output_parts.append(fk_info)

            # Indexes
            if indexes:
                output_parts.append("\nIndexes:")
                for idx in indexes:
                    idx_info = f"  - {idx['name']}: {idx['column_names']}"
                    if idx.get('unique'):
                        idx_info += " (UNIQUE)"
                    output_parts.append(idx_info)

            return "\n".join(output_parts)
        except Exception as e:
            return f"Error describing table: {str(e)}"

    @tool
    async def list_schemas(self) -> str:
        """
        List all schemas in the database.

        Returns:
            A formatted string listing all schema names
        """
        try:
            schemas = self.inspector.get_schema_names()
            if not schemas:
                return "No schemas found in the database."
            return "Schemas in database:\n" + "\n".join(
                f"  - {schema}" for schema in schemas
            )
        except Exception as e:
            return f"Error listing schemas: {str(e)}"
