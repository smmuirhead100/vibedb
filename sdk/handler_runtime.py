"""Runtime for executing cached query handlers.

A cached entry is a small async Python function the agent wrote while handling a
request live. It captures both the SQL it ran *and* the transformation it applied to
reshape rows into the application schema, so a cache hit can reproduce the whole thing
without invoking the LLM.

The handler contract:

    async def handler(execute_query, params):
        rows = await execute_query("SELECT ... WHERE last_name = :last_name", params)
        return [{"id": r["id"], "phone": r["phone_number"]} for r in rows]

- execute_query(sql, params) -> list[dict]: a narrow async callable (see make_executor).
- params: dict[str, str] of values extracted from the natural-language message.
- returns model-shaped dicts (single dict or list) which the client validates.

NOTE: this exec's LLM-generated code. Sandboxing is intentionally out of scope for now;
make_executor hands handlers only a narrow query callable rather than the full
DatabaseService to keep the blast radius small.
"""

from typing import Any, Awaitable, Callable

from sdk.casting import _rows_to_dicts
from sdk.database_service import DatabaseService, ExecuteQueryError

HANDLER_NAME = "handler"

# An async callable a handler uses to run SQL: (sql, params) -> list of row dicts.
Executor = Callable[..., Awaitable[list[dict[str, Any]]]]


def make_executor(db_service: DatabaseService) -> Executor:
    """Build the narrow execute_query callable handed to a cached handler."""

    async def execute_query(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        result = await db_service.execute_query(sql, params)
        if isinstance(result, ExecuteQueryError):
            raise Exception(result.message)
        return _rows_to_dicts(result)

    return execute_query


async def run_handler(handler_source: str, executor: Executor, params: dict[str, Any]) -> Any:
    """Compile and run a cached handler, returning its (model-shaped) output."""
    namespace: dict[str, Any] = {}
    exec(handler_source, namespace)
    handler = namespace.get(HANDLER_NAME)
    if handler is None:
        raise ValueError(f"Cached handler must define an async `{HANDLER_NAME}` function.")
    return await handler(executor, params)
