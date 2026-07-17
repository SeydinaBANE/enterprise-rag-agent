from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.domain.config import settings
from tests.conftest import MockLLMClient


@pytest.fixture(scope="module")
def integration_client() -> TestClient:
    """Requires a real ChromaDB instance running on CHROMA_HOST:CHROMA_PORT."""
    from src.agent.graph import build_agent
    from src.agent.memory import InMemorySessionStore
    from src.agent.tools import RAGSearchTool
    from src.infra.vector_store import ChromaVectorStore
    from src.rag.embedder import Embedder
    from src.rag.ingestion.pipeline import IngestPipeline

    mock_llm = MockLLMClient()
    vector_store = ChromaVectorStore()
    embedder = Embedder(mock_llm)
    rag_tool = RAGSearchTool(vector_store, embedder)
    session_store = InMemorySessionStore()
    pipeline = IngestPipeline(vector_store, embedder)
    agent = build_agent(mock_llm, rag_tool, session_store)

    app = create_app()
    app.state.llm_client = mock_llm
    app.state.vector_store = vector_store
    app.state.embedder = embedder
    app.state.session_store = session_store
    app.state.pipeline = pipeline
    app.state.agent = agent

    return TestClient(app)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_and_chat_e2e(integration_client: TestClient) -> None:
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("Enterprise AI enables autonomous task execution across business systems.")
        path = f.name

    try:
        with open(path, "rb") as fh:
            ingest_response = integration_client.post(
                "/documents/ingest",
                files={"file": ("test_doc.txt", fh, "text/plain")},
                headers={"X-API-Key": settings.api_key},
            )
        assert ingest_response.status_code == 200
        assert ingest_response.json()["chunks_stored"] >= 1

        integration_client.app.state.llm_client.complete.side_effect = [
            "RAG",
            "Enterprise AI autonomously executes tasks.",
        ]

        chat_response = integration_client.post(
            "/chat",
            json={"message": "What does enterprise AI do?", "session_id": "e2e-1"},
            headers={"X-API-Key": settings.api_key},
        )
        assert chat_response.status_code == 200
        data = chat_response.json()
        assert "answer" in data
    finally:
        os.unlink(path)
