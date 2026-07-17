from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import ChatResponse, Chunk


class IChatUseCase(ABC):
    @abstractmethod
    async def invoke(self, request_message: str, session_id: str) -> ChatResponse: ...


class IIngestUseCase(ABC):
    @abstractmethod
    async def run(self, source: str) -> list[Chunk]: ...
