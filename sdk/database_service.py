from ast import Dict
from typing import Any
from pydantic import BaseModel
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


class ExecuteQueryRowValueResult(BaseModel):
    column: str
    value: Any


class ExecuteQueryRowResult(BaseModel):
    values: list[ExecuteQueryRowValueResult]


class ExecuteQueryResult(BaseModel):
    rows: list[ExecuteQueryRowResult]


class ExecuteQueryError(BaseModel):
    message: str


class DatabaseService:
    def __init__(self, db_url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(_to_async_url(db_url))

    async def execute_query(self, query: str, params: dict[str, Any] | None = None) -> ExecuteQueryResult | ExecuteQueryError:
        try:
            async with self.engine.begin() as connection:
                result = await connection.execute(text(query), params or {})

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
            return ExecuteQueryError(message=f"Error executing query: {str(e)}")
        except Exception as e:
            return ExecuteQueryError(message=f"Unexpected error: {str(e)}")

    async def get_overview_of_database(self) -> str:
        try:
            async with self.engine.connect() as connection:
                # Tables
                tables_result = await connection.execute(text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' ORDER BY table_name"
                ))
                tables = [row[0] for row in tables_result.fetchall()]

                if not tables:
                    return "No tables found in the database."

                # Columns
                columns_result = await connection.execute(text(
                    "SELECT table_name, column_name, data_type, is_nullable, column_default "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "ORDER BY table_name, ordinal_position"
                ))
                columns_by_table: dict[str, list] = {}
                for row in columns_result.fetchall():
                    columns_by_table.setdefault(row[0], []).append(row[1:])

                # All constraints grouped by (table, constraint_name, type) -> [columns]
                constraints_result = await connection.execute(text(
                    "SELECT tc.table_name, tc.constraint_name, tc.constraint_type, "
                    "       kcu.column_name, kcu.ordinal_position "
                    "FROM information_schema.table_constraints tc "
                    "JOIN information_schema.key_column_usage kcu "
                    "  ON tc.constraint_name = kcu.constraint_name "
                    "  AND tc.table_schema = kcu.table_schema "
                    "WHERE tc.table_schema = 'public' "
                    "  AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE') "
                    "ORDER BY tc.table_name, tc.constraint_name, kcu.ordinal_position"
                ))
                # {table -> {constraint_name -> {"type": ..., "columns": [...]}}}
                constraints_by_table: dict[str, dict] = {}
                for table_name, constraint_name, constraint_type, column_name, _ in constraints_result.fetchall():
                    tbl = constraints_by_table.setdefault(table_name, {})
                    if constraint_name not in tbl:
                        tbl[constraint_name] = {"type": constraint_type, "columns": []}
                    tbl[constraint_name]["columns"].append(column_name)

                # Derive per-column PK membership and compound-vs-single unique sets
                pk_columns: dict[str, set] = {}
                # single-column uniques (annotated inline)
                single_uq_columns: dict[str, set] = {}
                # compound uniques (shown as table-level note)
                compound_uqs: dict[str, list[list[str]]] = {}

                for table_name, constraints in constraints_by_table.items():
                    for constraint in constraints.values():
                        cols = constraint["columns"]
                        if constraint["type"] == "PRIMARY KEY":
                            pk_columns.setdefault(table_name, set()).update(cols)
                        elif constraint["type"] == "UNIQUE":
                            if len(cols) == 1:
                                single_uq_columns.setdefault(table_name, set()).add(cols[0])
                            else:
                                compound_uqs.setdefault(table_name, []).append(cols)

                # Foreign keys
                fk_result = await connection.execute(text(
                    "SELECT kcu.table_name, tc.constraint_name, kcu.column_name, "
                    "       ccu.table_name AS foreign_table, ccu.column_name AS foreign_column, "
                    "       kcu.ordinal_position "
                    "FROM information_schema.table_constraints tc "
                    "JOIN information_schema.key_column_usage kcu "
                    "  ON tc.constraint_name = kcu.constraint_name "
                    "  AND tc.table_schema = kcu.table_schema "
                    "JOIN information_schema.constraint_column_usage ccu "
                    "  ON ccu.constraint_name = tc.constraint_name "
                    "  AND ccu.table_schema = tc.table_schema "
                    "WHERE tc.constraint_type = 'FOREIGN KEY' "
                    "  AND tc.table_schema = 'public' "
                    "ORDER BY kcu.table_name, tc.constraint_name, kcu.ordinal_position"
                ))
                # {table -> {constraint_name -> {"local": [...], "foreign_table": ..., "foreign": [...]}}}
                fk_by_table: dict[str, dict] = {}
                for table_name, constraint_name, col, foreign_table, foreign_col, _ in fk_result.fetchall():
                    tbl = fk_by_table.setdefault(table_name, {})
                    if constraint_name not in tbl:
                        tbl[constraint_name] = {"local": [], "foreign_table": foreign_table, "foreign": []}
                    tbl[constraint_name]["local"].append(col)
                    tbl[constraint_name]["foreign"].append(foreign_col)

            # Build output
            parts = ["DATABASE OVERVIEW", "=" * 60, ""]

            for table in tables:
                parts.append(f"TABLE: {table}")
                parts.append("-" * 40)

                cols = columns_by_table.get(table, [])
                pks = pk_columns.get(table, set())
                single_uqs = single_uq_columns.get(table, set())

                for col_name, data_type, is_nullable, col_default in cols:
                    tags = []
                    if col_name in pks:
                        tags.append("PK")
                    if col_name in single_uqs:
                        tags.append("UNIQUE")
                    if is_nullable == "NO":
                        tags.append("NOT NULL")
                    if col_default is not None:
                        tags.append(f"DEFAULT={col_default}")

                    tag_str = f"  [{', '.join(tags)}]" if tags else ""
                    parts.append(f"  {col_name}: {data_type}{tag_str}")

                # Compound unique constraints as table-level notes
                for compound_cols in compound_uqs.get(table, []):
                    parts.append(f"  UNIQUE({', '.join(compound_cols)})")

                # Foreign keys — group compound FKs onto one line
                fks = fk_by_table.get(table, {})
                if fks:
                    parts.append("  Foreign Keys:")
                    for fk in fks.values():
                        local = ", ".join(fk["local"])
                        foreign = ", ".join(fk["foreign"])
                        if len(fk["local"]) > 1:
                            parts.append(f"    ({local}) -> {fk['foreign_table']}.({foreign})")
                        else:
                            parts.append(f"    {local} -> {fk['foreign_table']}.{foreign}")

                parts.append("")

            return "\n".join(parts)

        except Exception as e:
            return f"Error retrieving database overview: {str(e)}"

    async def dispose(self) -> None:
        await self.engine.dispose()
