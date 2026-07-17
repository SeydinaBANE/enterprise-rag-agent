from __future__ import annotations

import ipaddress
import socket
import uuid
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from src.domain.config import settings
from src.domain.exceptions import UnsupportedSourceError
from src.domain.models import Document
from src.domain.ports import IDocumentLoader

_MAX_REDIRECTS = 5

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("::ffff:0:0/96"),
]


def _is_private_host(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        pass
    try:
        resolved = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except OSError:
        return True
    for _family, _, _, _, sockaddr in resolved:
        addr = ipaddress.ip_address(sockaddr[0])
        if any(addr in net for net in _PRIVATE_NETWORKS):
            return True
    return False


def _validate_url(source: str) -> None:
    from urllib.parse import urlparse

    parsed = urlparse(source)
    host = parsed.hostname or ""
    if _is_private_host(host):
        raise UnsupportedSourceError(f"URL resolves to a private address: {host}")
    allowed = settings.allowed_url_domains
    if allowed:
        allowed_domains = [d.strip() for d in allowed.split(",") if d.strip()]
        if allowed_domains and not any(host.endswith(d) for d in allowed_domains):
            raise UnsupportedSourceError(f"Domain {host} is not in the allowed list: {allowed}")


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
        url = source
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(15.0, connect=5.0),
        ) as client:
            for _ in range(_MAX_REDIRECTS + 1):
                _validate_url(url)
                response = await client.get(url)
                if not response.is_redirect:
                    break
                location = response.headers.get("location")
                if not location:
                    break
                url = str(response.url.join(location))
            else:
                raise UnsupportedSourceError(f"Too many redirects for: {source}")
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
