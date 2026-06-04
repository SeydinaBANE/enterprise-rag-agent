from __future__ import annotations

import uuid
from typing import Any

import chromadb
from chromadb.api import AsyncClientAPI
from chromadb.api.models.AsyncCollection import AsyncCollection

from src.core.config import settings
from src.core.exceptions import VectorStoreError
from src.core.models import Chunk
from src.core.ports import IVectorStore

COLLECTION_NAME = "documents"


class ChromaVectorStore(IVectorStore):
    def __init__(self) -> None:
        self._host = settings.chroma_host
        self._port = settings.chroma_port
        self._client: AsyncClientAPI | None = None

    async def _get_client(self) -> AsyncClientAPI:
        if self._client is None:
            self._client = await chromadb.AsyncHttpClient(
                host=self._host,
                port=self._port,
            )
        return self._client

    async def _get_collection(self) -> AsyncCollection:
        client = await self._get_client()
        return await client.get_or_create_collection(COLLECTION_NAME)

    async def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        try:
            collection = await self._get_collection()
            await collection.add(
                ids=[c.id for c in chunks],
                embeddings=[[float(v) for v in c.embedding] for c in chunks],  # type: ignore[arg-type]  # chromadb stubs expect numpy
                documents=[c.content for c in chunks],
                metadatas=[{"document_id": c.document_id, "source": c.source} for c in chunks],
            )
        except Exception as exc:
            raise VectorStoreError(str(exc)) from exc

    async def search(self, query_embedding: list[float], top_k: int) -> list[Chunk]:
        try:
            collection = await self._get_collection()
            results = await collection.query(
                query_embeddings=[[float(v) for v in query_embedding]],  # type: ignore[arg-type]  # chromadb stubs expect numpy
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
            results_any: dict[str, Any] = dict(results)
            raw_docs: list[str] = (results_any.get("documents") or [[]])[0]
            raw_metas: list[dict[str, Any]] = (results_any.get("metadatas") or [[]])[0]

            return [
                Chunk(
                    id=str(uuid.uuid4()),
                    document_id=str(raw_metas[i].get("document_id", "")),
                    content=doc,
                    source=str(raw_metas[i].get("source", "")),
                )
                for i, doc in enumerate(raw_docs)
            ]
        except Exception as exc:
            raise VectorStoreError(str(exc)) from exc

    async def list_documents(self) -> list[tuple[str, int]]:
        try:
            collection = await self._get_collection()
            result = await collection.get(include=["metadatas"])
            raw_metas: list[dict[str, Any]] = result.get("metadatas") or []  # type: ignore[assignment]
            counts: dict[str, int] = {}
            for meta in raw_metas:
                doc_id = str(meta.get("document_id", ""))
                counts[doc_id] = counts.get(doc_id, 0) + 1
            return list(counts.items())
        except Exception as exc:
            raise VectorStoreError(str(exc)) from exc

    async def is_healthy(self) -> bool:
        try:
            client = await self._get_client()
            await client.heartbeat()
            return True
        except Exception:
            return False
