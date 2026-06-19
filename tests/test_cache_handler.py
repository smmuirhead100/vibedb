"""Deterministic tests for the cached-handler path (no LLM, no real DB).

Run with: uv run python tests/test_cache_handler.py
"""

import asyncio

from pydantic import BaseModel

from sdk.casting import cast_result
from sdk.handler_runtime import run_handler
from sdk.query_cache import QueryCache


class User(BaseModel):
    id: int
    first_name: str
    phone: str  # app schema: differs from the DB column `phone_number`


# A handler such as the LLM would write: runs SQL via the narrow executor, then
# reshapes DB columns (phone_number) into the app schema (phone).
HANDLER_SOURCE = (
    "async def handler(execute_query, params):\n"
    "    rows = await execute_query('SELECT * FROM users WHERE id = :id', params)\n"
    "    return [{'id': r['id'], 'first_name': r['first_name'], 'phone': r['phone_number']} for r in rows]\n"
)


def make_fake_executor(captured):
    """Executor that records the SQL/params it was called with and returns canned rows."""

    async def execute_query(sql, params=None):
        captured["sql"] = sql
        captured["params"] = params
        return [
            {"id": 7, "first_name": "James", "last_name": "Smith", "phone_number": "555-0101"},
        ]

    return execute_query


async def test_handler_runs_and_transforms():
    captured = {}
    result = await run_handler(HANDLER_SOURCE, make_fake_executor(captured), {"id": "7"})

    assert captured["sql"] == "SELECT * FROM users WHERE id = :id", captured["sql"]
    assert captured["params"] == {"id": "7"}, captured["params"]
    # Handler dropped last_name and renamed phone_number -> phone.
    assert result == [{"id": 7, "first_name": "James", "phone": "555-0101"}], result


async def test_handler_output_casts_into_model():
    result = await run_handler(HANDLER_SOURCE, make_fake_executor({}), {"id": "7"})
    users = cast_result(result, list[User])

    assert len(users) == 1
    assert isinstance(users[0], User)
    assert users[0].phone == "555-0101"  # populated despite the DB column being phone_number


async def test_cache_match_extracts_params():
    cache = QueryCache()
    cache.add("Get user with id {id}", HANDLER_SOURCE)

    assert cache.get_cached_query("Get user with id 7") == (HANDLER_SOURCE, {"id": "7"})
    assert cache.get_cached_query("Totally unrelated message") is None


async def test_missing_handler_function_raises():
    try:
        await run_handler("x = 1\n", make_fake_executor({}), {})
    except ValueError:
        return
    raise AssertionError("expected ValueError when source defines no `handler`")


async def main():
    await test_handler_runs_and_transforms()
    await test_handler_output_casts_into_model()
    await test_cache_match_extracts_params()
    await test_missing_handler_function_raises()
    print("All cache-handler tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
