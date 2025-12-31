from enum import Enum

from pydantic import BaseModel
from typing import List

from agents.core.tools import ToolCall


class ChatRole(Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"


class ChatMessage(BaseModel):
    role: ChatRole
    content: str | ToolCall
