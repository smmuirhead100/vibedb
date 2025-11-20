from enum import Enum

from pydantic import BaseModel

from agents.tools import ToolCall


class ChatRole(Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class ChatMessage(BaseModel):
    role: ChatRole
    content: str | ToolCall
