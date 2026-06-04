from __future__ import annotations

import uuid
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from src.core.exceptions import UnsupportedSourceError
from src.core.models import Document
from src.core.ports import IDocumentLoader


class PDFLoader(IDocumentLoader):
    async def load(self, source: str) -> list[Document]:
        reader = PdfReader(source)
        pages = [page.extract_text() or "" for page in reader.pages]
        content = "\n\n".join(p for p in pages if p.strip())
        return [Document(id=str(uuid.uuid4()), content=content, source=source)]


class TextLoader(IDocumentLoader):
    async def load(self, source: str) -> list[Document]:
        content = Path(source).read_text(encoding="utf-8")
        return [Document(id=str(uuid.uuid4()), content=content, source=source)]


class URLLoader(IDocumentLoader):
    async def load(self, source: str) -> list[Document]:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            response = await client.get(source)
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        content = soup.get_text(separator="\n", strip=True)
        return [Document(id=str(uuid.uuid4()), content=content, source=source)]


def get_loader(source: str) -> IDocumentLoader:
    if source.startswith(("http://", "https://")):
        return URLLoader()
    path = Path(source)
    if path.suffix.lower() == ".pdf":
        return PDFLoader()
    if path.suffix.lower() in {".txt", ".md", ".rst"}:
        return TextLoader()
    raise UnsupportedSourceError(f"No loader for: {source}")
