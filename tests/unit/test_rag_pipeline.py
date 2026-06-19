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


@pytest.mark.asyncio
async def test_embed_one_raises_on_empty_response(mock_llm: MockLLMClient) -> None:
    from src.core.exceptions import EmbeddingError

    mock_llm.embed.return_value = []
    embedder = Embedder(mock_llm)
    with pytest.raises(EmbeddingError):
        await embedder.embed_one("hello")


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


def test_is_private_host() -> None:
    from src.rag.ingestion.loader import _is_private_host

    assert _is_private_host("127.0.0.1") is True
    assert _is_private_host("10.0.0.5") is True
    assert _is_private_host("192.168.1.1") is True
    assert _is_private_host("172.16.0.1") is True
    assert _is_private_host("169.254.1.1") is True
    assert _is_private_host("8.8.8.8") is False
    assert _is_private_host("::1") is True
    assert _is_private_host("invalid-host-that-does-not-exist-12345") is True  # OSError → private


def test_get_loader_url_validates_private_ip() -> None:
    from src.core.exceptions import UnsupportedSourceError
    from src.rag.ingestion.loader import URLLoader

    loader = URLLoader()
    assert loader is not None

    from src.rag.ingestion.loader import _validate_url

    with pytest.raises(UnsupportedSourceError):
        _validate_url("http://127.0.0.1:5000/admin")

    with pytest.raises(UnsupportedSourceError):
        _validate_url("http://10.0.0.1/secret")


def test_get_loader_url_validates_hostname() -> None:
    from src.core.exceptions import UnsupportedSourceError
    from src.rag.ingestion.loader import _validate_url

    with pytest.raises(UnsupportedSourceError):
        _validate_url("http://localhost:8000/internal")


def test_get_loader_url_validates_allowed_domains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.config import settings
    from src.core.exceptions import UnsupportedSourceError

    monkeypatch.setattr(settings, "allowed_url_domains", "example.com")
    from src.rag.ingestion.loader import _validate_url

    with pytest.raises(UnsupportedSourceError):
        _validate_url("http://evil.com/data")


def test_get_loader_url_allows_public_domain() -> None:
    from src.rag.ingestion.loader import _validate_url

    _validate_url("https://example.com/page")
    _validate_url("https://www.wikipedia.org")


@pytest.mark.asyncio
async def test_url_loader_loads_content() -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    from src.rag.ingestion.loader import URLLoader

    mock_response = MagicMock()
    mock_response.text = "<html><body>Hello world</body></html>"
    mock_response.is_redirect = False
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        loader = URLLoader()
        docs = await loader.load("https://example.com/page")

    assert len(docs) == 1
    assert "Hello world" in docs[0].content


@pytest.mark.asyncio
async def test_url_loader_http_error() -> None:
    from unittest.mock import AsyncMock, patch

    import httpx

    from src.rag.ingestion.loader import URLLoader  # noqa: I001

    async def _raise(*args: object, **kwargs: object) -> None:
        raise httpx.HTTPStatusError("404", request=None, response=None)  # type: ignore[call-arg]

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=_raise)

        loader = URLLoader()
        with pytest.raises(httpx.HTTPStatusError):
            await loader.load("https://example.com/notfound")


@pytest.mark.asyncio
async def test_url_loader_rejects_private_ip() -> None:
    from src.core.exceptions import UnsupportedSourceError
    from src.rag.ingestion.loader import URLLoader

    loader = URLLoader()
    with pytest.raises(UnsupportedSourceError):
        await loader.load("http://127.0.0.1:5000/admin")


def test_is_private_host_ipv6_and_wildcard() -> None:
    from src.rag.ingestion.loader import _is_private_host

    assert _is_private_host("::1") is True
    assert _is_private_host("fe80::1") is True
    assert _is_private_host("fc00::1") is True
    assert _is_private_host("0.0.0.0") is True
    assert _is_private_host("2606:4700:4700::1111") is False


@pytest.mark.asyncio
async def test_url_loader_rejects_redirect_to_private_ip() -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    from src.core.exceptions import UnsupportedSourceError
    from src.rag.ingestion.loader import URLLoader

    redirect_response = MagicMock()
    redirect_response.is_redirect = True
    redirect_response.headers = {"location": "http://169.254.169.254/latest/meta-data/"}
    redirect_response.url.join.return_value = "http://169.254.169.254/latest/meta-data/"

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=redirect_response
        )

        loader = URLLoader()
        with pytest.raises(UnsupportedSourceError):
            await loader.load("https://example.com/redirect")


@pytest.mark.asyncio
async def test_pdf_loader_loads_content() -> None:
    from io import BytesIO

    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(612, 792)
    buf = BytesIO()
    writer.write(buf)
    buf.seek(0)

    import os
    import tempfile

    from src.rag.ingestion.loader import PDFLoader

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(buf.getvalue())
        path = f.name

    try:
        loader = PDFLoader()
        docs = await loader.load(path)
        assert len(docs) == 1
    finally:
        os.unlink(path)


@pytest.mark.asyncio
async def test_url_loader_strips_tags() -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    from src.rag.ingestion.loader import URLLoader

    mock_response = MagicMock()
    mock_response.text = "<html><body><nav>Navbar</nav><div>Content</div></body></html>"
    mock_response.is_redirect = False
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        loader = URLLoader()
        docs = await loader.load("https://example.com/page")

    assert len(docs) == 1
    assert "Navbar" not in docs[0].content
    assert "Content" in docs[0].content


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
