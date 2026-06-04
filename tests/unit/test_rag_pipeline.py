from __future__ import annotations

import pytest

from src.core.models import Chunk, Document
from src.rag.embedder import Embedder
from src.rag.ingestion.pipeline import IngestPipeline
from src.rag.ingestion.splitter import TextSplitter
from src.rag.retriever import Retriever
from tests.conftest import MockLLMClient, MockVectorStore


@pytest.mark.asyncio
async def test_embedder_delegates_to_llm_client(mock_llm: MockLLMClient) -> None:
    mock_llm.embed.return_value = [[0.5] * 10, [0.3] * 10]
    embedder = Embedder(mock_llm)
    result = await embedder.embed(["hello", "world"])
    assert len(result) == 2
    mock_llm.embed.assert_called_once_with(["hello", "world"])


@pytest.mark.asyncio
async def test_embedder_empty_input(mock_llm: MockLLMClient) -> None:
    embedder = Embedder(mock_llm)
    result = await embedder.embed([])
    assert result == []
    mock_llm.embed.assert_not_called()


def test_splitter_basic_split() -> None:
    doc = Document(id="d1", content="word " * 100, source="test.txt")
    splitter = TextSplitter(chunk_size=10, chunk_overlap=2)
    chunks = splitter.split(doc)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.document_id == "d1"


def test_splitter_empty_document() -> None:
    doc = Document(id="d1", content="   ", source="test.txt")
    splitter = TextSplitter(chunk_size=10, chunk_overlap=2)
    chunks = splitter.split(doc)
    assert chunks == []


def test_splitter_short_document() -> None:
    doc = Document(id="d1", content="hello world", source="test.txt")
    splitter = TextSplitter(chunk_size=50, chunk_overlap=5)
    chunks = splitter.split(doc)
    assert len(chunks) == 1
    assert chunks[0].content == "hello world"


@pytest.mark.asyncio
async def test_pipeline_stores_chunks(
    mock_llm: MockLLMClient, mock_vector_store: MockVectorStore
) -> None:
    mock_llm.embed.side_effect = lambda texts: [[0.1] * 10] * len(texts)
    embedder = Embedder(mock_llm)
    splitter = TextSplitter(chunk_size=5, chunk_overlap=1)
    pipeline = IngestPipeline(mock_vector_store, embedder, splitter)

    import os
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("word " * 50)
        path = f.name

    try:
        chunks = await pipeline.run(path)
        assert len(chunks) > 0
        mock_vector_store.add_chunks.assert_called_once()
    finally:
        os.unlink(path)


def test_get_loader_txt() -> None:
    from src.rag.ingestion.loader import TextLoader, get_loader

    assert isinstance(get_loader("document.txt"), TextLoader)


def test_get_loader_md() -> None:
    from src.rag.ingestion.loader import TextLoader, get_loader

    assert isinstance(get_loader("notes.md"), TextLoader)


def test_get_loader_pdf() -> None:
    from src.rag.ingestion.loader import PDFLoader, get_loader

    assert isinstance(get_loader("report.pdf"), PDFLoader)


def test_get_loader_url() -> None:
    from src.rag.ingestion.loader import URLLoader, get_loader

    assert isinstance(get_loader("https://example.com/page"), URLLoader)


def test_get_loader_unsupported() -> None:
    from src.core.exceptions import UnsupportedSourceError
    from src.rag.ingestion.loader import get_loader

    with pytest.raises(UnsupportedSourceError):
        get_loader("document.docx")


@pytest.mark.asyncio
async def test_retriever_returns_chunks(
    mock_llm: MockLLMClient,
    mock_vector_store: MockVectorStore,
    sample_chunk: Chunk,
) -> None:
    mock_llm.embed.return_value = [[0.1] * 384]
    mock_vector_store.search.return_value = [sample_chunk]
    embedder = Embedder(mock_llm)
    retriever = Retriever(mock_vector_store, embedder)
    results = await retriever.search("enterprise AI", top_k=3)
    assert len(results) == 1
    assert results[0].document_id == "doc-1"
