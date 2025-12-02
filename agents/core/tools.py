from typing import Any, Dict, Type
from pydantic import BaseModel


class Tool(BaseModel):
    name: str
    description: str
    input_schema: Type[BaseModel]


class ToolCall(BaseModel):
    id: str
    tool: Tool
    args: Dict[str, Any]
    response: str

# class User(BaseModel):
#     name: str = Field(description="The user's full name")
#     age: int = Field(ge=0, description="The user's age in years")


# tool = Tool(name="user", schema=User)
# print(tool.schema.model_json_schema())