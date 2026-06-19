from typing import Any, Type, get_args, get_origin

from pydantic import BaseModel

from sdk.database_service import ExecuteQueryResult


def _rows_to_dicts(result: ExecuteQueryResult) -> list[dict[str, Any]]:
    """Flatten an ExecuteQueryResult into a list of {column: value} dicts."""
    return [
        {value.column: value.value for value in row.values}
        for row in result.rows
    ]


def cast_result(data: Any, return_as: Type[Any] | None) -> Any:
    """Cast raw query data into the caller's requested type.

    `data` may be an ExecuteQueryResult (from the cache path), a single dict, or a
    list of dicts (what the LLM passes to the cast_result tool).

    `return_as` may be a Pydantic model, list[Model], or None. When None, the data is
    returned as plain dicts without validation.
    """
    if isinstance(data, ExecuteQueryResult):
        data = _rows_to_dicts(data)

    if return_as is None:
        return data

    origin = get_origin(return_as)
    if origin is list:
        args = get_args(return_as)
        item_type = args[0] if args else None
        rows = data if isinstance(data, list) else [data]
        if isinstance(item_type, type) and issubclass(item_type, BaseModel):
            return [item_type.model_validate(row) for row in rows]
        return rows

    if isinstance(return_as, type) and issubclass(return_as, BaseModel):
        row = data[0] if isinstance(data, list) else data
        return return_as.model_validate(row)

    return data
