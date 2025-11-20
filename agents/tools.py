from typing import Type
from pydantic import BaseModel, Field


class Tool(BaseModel):
    name: str
    schema: Type[BaseModel]


class ToolCall(BaseModel):
    tool: Tool
    response: str

# class User(BaseModel):
#     name: str = Field(description="The user's full name")
#     age: int = Field(ge=0, description="The user's age in years")


# tool = Tool(name="user", schema=User)
# print(tool.schema.model_json_schema())