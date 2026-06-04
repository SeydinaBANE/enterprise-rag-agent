from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.models import ChatMessage, Chunk, Document


class IDocumentLoader(ABC):
    @abstractmethod
    async def load(self, source: str) -> list[Document]: ...


class IVectorStore(ABC):
    @abstractmethod
    async def add_chunks(self, chunks: list[Chunk]) -> None: ...

    @abstractmethod
    async def search(self, query_embedding: list[float], top_k: int) -> list[Chunk]: ...

    @abstractmethod
    async def list_documents(self) -> list[tuple[str, int]]: ...

    @abstractmethod
    async def is_healthy(self) -> bool: ...


class ILLMClient(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> str: ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    async def is_healthy(self) -> bool: ...


class ISessionStore(ABC):
    @abstractmethod
    async def get_history(self, session_id: str) -> list[ChatMessage]: ...

    @abstractmethod
    async def add_message(self, session_id: str, message: ChatMessage) -> None: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def is_healthy(self) -> bool: ...
