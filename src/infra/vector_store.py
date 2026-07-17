from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import chromadb
from chromadb.api import AsyncClientAPI
from chromadb.api.models.AsyncCollection import AsyncCollection

from src.domain.config import settings
from src.domain.exceptions import VectorStoreError
from src.domain.models import Chunk
from src.domain.ports import IVectorStore

COLLECTION_NAME = "documents"


class ChromaVectorStore(IVectorStore):
    def __init__(self) -> None:
        self._client: AsyncClientAPI | None = None

    async def _get_client(self) -> AsyncClientAPI:
        if self._client is None:
            if settings.chroma_mode == "embedded":
                self._client = await chromadb.AsyncPersistentClient(  # type: ignore[attr-defined]  # stubs lag runtime API
                    path=settings.chroma_data_path
                )
            else:
                self._client = await chromadb.AsyncHttpClient(
                    host=settings.chroma_host,
                    port=settings.chroma_port,
                )
        return self._client

    async def _get_collection(self) -> AsyncCollection:
        client = await self._get_client()
        return await client.get_or_create_collection(COLLECTION_NAME)

    async def _check_dimension(self, embedding_dim: int) -> None:
        collection = await self._get_collection()
        count_result = await collection.count()
        if count_result == 0:
            return
        existing = await collection.get(limit=1, include=["embeddings"])
        existing_embeddings = existing.get("embeddings")
        if existing_embeddings and len(existing_embeddings) > 0:
            existing_dim = len(existing_embeddings[0])
            if existing_dim != embedding_dim:
                raise VectorStoreError(
                    f"Dimension mismatch: existing collection has {existing_dim} dimensions, "
                    f"got {embedding_dim}. Delete the collection or change the embedding model."
                )

    async def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        try:
            embedding_dim = len(chunks[0].embedding)
            await self._check_dimension(embedding_dim)
            collection = await self._get_collection()
            now = datetime.utcnow().isoformat()
            await collection.add(
                ids=[c.id for c in chunks],
                embeddings=[[float(v) for v in c.embedding] for c in chunks],  # type: ignore[arg-type]  # chromadb stubs expect numpy
                documents=[c.content for c in chunks],
                metadatas=[
                    {"document_id": c.document_id, "source": c.source, "ingested_at": now}
                    for c in chunks
                ],
            )
        except VectorStoreError:
            raise
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

    async def list_documents(self) -> list[tuple[str, int, str]]:
        try:
            collection = await self._get_collection()
            result = await collection.get(include=["metadatas"])
            raw_metas: list[dict[str, Any]] = result.get("metadatas") or []  # type: ignore[assignment]
            doc_map: dict[str, tuple[int, str]] = {}
            for meta in raw_metas:
                doc_id = str(meta.get("document_id", ""))
                ingested = str(meta.get("ingested_at", ""))
                if doc_id in doc_map:
                    cnt, _ = doc_map[doc_id]
                    doc_map[doc_id] = (cnt + 1, ingested)
                else:
                    doc_map[doc_id] = (1, ingested)
            return [(did, cnt, ingested) for did, (cnt, ingested) in doc_map.items()]
        except Exception as exc:
            raise VectorStoreError(str(exc)) from exc

    async def is_healthy(self) -> bool:
        try:
            client = await self._get_client()
            await client.heartbeat()
            return True
        except Exception:
            return False
