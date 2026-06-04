from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.core.models import Chunk


class MockLLMClient:
    def __init__(self, completion_text: str = "Test answer") -> None:
        self._text = completion_text
        self.complete: AsyncMock = AsyncMock(return_value=completion_text)
        self.embed: AsyncMock = AsyncMock(return_value=[[0.1] * 384])
        self.is_healthy: AsyncMock = AsyncMock(return_value=True)


class MockVectorStore:
    def __init__(self, chunks: list[Chunk] | None = None) -> None:
        self._chunks = chunks or []
        self.add_chunks: AsyncMock = AsyncMock()
        self.search: AsyncMock = AsyncMock(return_value=self._chunks)
        self.list_documents: AsyncMock = AsyncMock(return_value=[])
        self.is_healthy: AsyncMock = AsyncMock(return_value=True)


class MockSessionStore:
    def __init__(self) -> None:
        self.get_history: AsyncMock = AsyncMock(return_value=[])
        self.add_message: AsyncMock = AsyncMock()
        self.count: AsyncMock = AsyncMock(return_value=0)
        self.is_healthy: AsyncMock = AsyncMock(return_value=True)


@pytest.fixture
def mock_llm() -> MockLLMClient:
    return MockLLMClient()


@pytest.fixture
def mock_vector_store() -> MockVectorStore:
    return MockVectorStore()


@pytest.fixture
def mock_session_store() -> MockSessionStore:
    return MockSessionStore()


@pytest.fixture
def sample_chunk() -> Chunk:
    return Chunk(
        id="chunk-1",
        document_id="doc-1",
        content="This is a test chunk about enterprise AI.",
        source="test.pdf",
        embedding=[0.1] * 384,
    )
