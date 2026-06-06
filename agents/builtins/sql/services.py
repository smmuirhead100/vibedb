from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def _to_async_url(db_url: str) -> str:
    if db_url.startswith("postgresql+asyncpg://"):
        return db_url
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if db_url.startswith("postgres://"):
        return db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return db_url


class DatabaseService:
    def __init__(self, db_url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(_to_async_url(db_url))

    async def execute_query(self, query: str) -> str:
        try:
            async with self.engine.begin() as connection:
                result = await connection.execute(text(query))

                if result.returns_rows:
                    rows = result.fetchall()
                    columns = result.keys()

                    if not rows:
                        return "Query executed successfully. No rows returned."

                    output_parts = []
                    header = " | ".join(str(col) for col in columns)
                    output_parts.append(header)
                    output_parts.append("-" * len(header))
                    for row in rows:
                        row_str = " | ".join(
                            str(val) if val is not None else "NULL" for val in row
                        )
                        output_parts.append(row_str)

                    return "\n".join(output_parts)

                rowcount = result.rowcount
                return f"Query executed successfully. Rows affected: {rowcount}"

        except SQLAlchemyError as e:
            return f"Error executing query: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    async def list_tables(self) -> str:
        try:
            async with self.engine.connect() as connection:
                result = await connection.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public' ORDER BY table_name"
                    )
                )
                tables = [row[0] for row in result.fetchall()]

            if not tables:
                return "No tables found in the database."
            return "Tables in database:\n" + "\n".join(
                f"  - {table}" for table in tables
            )
        except Exception as e:
            return f"Error listing tables: {str(e)}"

    async def list_schemas(self) -> str:
        try:
            async with self.engine.connect() as connection:
                result = await connection.execute(
                    text(
                        "SELECT schema_name FROM information_schema.schemata "
                        "WHERE schema_name NOT IN ('pg_catalog', 'information_schema') "
                        "ORDER BY schema_name"
                    )
                )
                schemas = [row[0] for row in result.fetchall()]

            if not schemas:
                return "No schemas found in the database."
            return "Schemas in database:\n" + "\n".join(
                f"  - {schema}" for schema in schemas
            )
        except Exception as e:
            return f"Error listing schemas: {str(e)}"

    async def dispose(self) -> None:
        await self.engine.dispose()
