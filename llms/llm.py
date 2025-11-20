# Abstract base class for LLMs
from abc import ABC, abstractmethod
from typing import AsyncGenerator


class LLM(ABC):
    @abstractmethod
    async def astream(
        self,
        prompt: str
    ) -> AsyncGenerator[str]:
        raise NotImplementedError("Subclasses must implement this method!")
