from __future__ import annotations

import pytest

from src.agent.graph import build_agent
from src.agent.memory import ConversationMemory, InMemorySessionStore
from src.agent.tools import RAGSearchTool
from src.core.models import ChatMessage, Chunk
from src.rag.embedder import Embedder
from tests.conftest import MockLLMClient, MockSessionStore, MockVectorStore


@pytest.fixture
def session_store() -> InMemorySessionStore:
    return InMemorySessionStore()


@pytest.fixture
def rag_tool(mock_llm: MockLLMClient, mock_vector_store: MockVectorStore) -> RAGSearchTool:
    embedder = Embedder(mock_llm)
    return RAGSearchTool(mock_vector_store, embedder)


@pytest.mark.asyncio
async def test_agent_invoke_direct_path(
    mock_llm: MockLLMClient,
    mock_vector_store: MockVectorStore,
    session_store: InMemorySessionStore,
    rag_tool: RAGSearchTool,
) -> None:
    mock_llm.complete.side_effect = ["DIRECT", "42 is the answer"]
    agent = build_agent(mock_llm, rag_tool, session_store)
    response = await agent.invoke("What is 6 times 7?", "session-1")
    assert response.answer == "42 is the answer"
    assert response.used_retrieval is False
    assert response.session_id == "session-1"


@pytest.mark.asyncio
async def test_agent_invoke_rag_path(
    mock_llm: MockLLMClient,
    mock_vector_store: MockVectorStore,
    session_store: InMemorySessionStore,
    rag_tool: RAGSearchTool,
    sample_chunk: Chunk,
) -> None:
    mock_vector_store.search.return_value = [sample_chunk]
    mock_llm.complete.side_effect = ["RAG", "Based on the doc, the answer is X"]
    agent = build_agent(mock_llm, rag_tool, session_store)
    response = await agent.invoke("Tell me about enterprise AI", "session-2")
    assert response.used_retrieval is True
    assert len(response.sources) == 1
    assert response.sources[0].document_id == "doc-1"


@pytest.mark.asyncio
async def test_agent_routing_ignores_rag_substring(
    mock_llm: MockLLMClient,
    mock_vector_store: MockVectorStore,
    session_store: InMemorySessionStore,
    rag_tool: RAGSearchTool,
) -> None:
    mock_llm.complete.side_effect = ["DIRECT (no storage needed)", "answer"]
    agent = build_agent(mock_llm, rag_tool, session_store)
    response = await agent.invoke("How are you?", "session-route")
    assert response.used_retrieval is False


@pytest.mark.asyncio
async def test_agent_latency_is_populated(
    mock_llm: MockLLMClient,
    mock_vector_store: MockVectorStore,
    session_store: InMemorySessionStore,
    rag_tool: RAGSearchTool,
) -> None:
    mock_llm.complete.side_effect = ["DIRECT", "answer"]
    agent = build_agent(mock_llm, rag_tool, session_store)
    response = await agent.invoke("Hello", "session-3")
    assert response.latency_ms >= 0


@pytest.mark.asyncio
async def test_agent_history_persists_across_turns(
    mock_llm: MockLLMClient,
    mock_vector_store: MockVectorStore,
    session_store: InMemorySessionStore,
    rag_tool: RAGSearchTool,
) -> None:
    mock_llm.complete.side_effect = ["DIRECT", "First answer", "DIRECT", "Second answer"]
    agent = build_agent(mock_llm, rag_tool, session_store)
    await agent.invoke("First question", "session-persist")
    await agent.invoke("Second question", "session-persist")
    history = await session_store.get_history("session-persist")
    assert len(history) == 4
    assert history[0].role == "user"
    assert history[1].role == "assistant"


@pytest.mark.asyncio
async def test_agent_uses_mock_session_store(
    mock_llm: MockLLMClient,
    mock_vector_store: MockVectorStore,
    mock_session_store: MockSessionStore,
    rag_tool: RAGSearchTool,
) -> None:
    mock_llm.complete.side_effect = ["DIRECT", "answer"]
    agent = build_agent(mock_llm, rag_tool, mock_session_store)
    await agent.invoke("Hello", "s1")
    mock_session_store.get_history.assert_called_once_with("s1")
    assert mock_session_store.add_message.call_count == 2


def test_conversation_memory_stores_messages() -> None:
    memory = ConversationMemory(max_turns=2)
    memory.add(ChatMessage(role="user", content="Hello"))
    memory.add(ChatMessage(role="assistant", content="Hi"))
    history = memory.get_history()
    assert len(history) == 2
    assert history[0].role == "user"


def test_conversation_memory_respects_max_turns() -> None:
    memory = ConversationMemory(max_turns=1)
    for i in range(5):
        memory.add(ChatMessage(role="user", content=f"msg {i}"))
        memory.add(ChatMessage(role="assistant", content=f"reply {i}"))
    assert len(memory.get_history()) == 2


@pytest.mark.asyncio
async def test_in_memory_session_store_isolation() -> None:
    store = InMemorySessionStore()
    await store.add_message("session-a", ChatMessage(role="user", content="hello a"))
    await store.add_message("session-b", ChatMessage(role="user", content="hello b"))
    history_a = await store.get_history("session-a")
    history_b = await store.get_history("session-b")
    assert len(history_a) == 1
    assert len(history_b) == 1
    assert history_a[0].content == "hello a"
    assert history_b[0].content == "hello b"
    assert await store.count() == 2
