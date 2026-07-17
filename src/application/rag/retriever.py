from __future__ import annotations

from src.application.rag.embedder import Embedder
from src.domain.config import settings
from src.domain.models import Chunk
from src.ports.outbound import IVectorStore


class Retriever:
    def __init__(self, vector_store: IVectorStore, embedder: Embedder) -> None:
        self._store = vector_store
        self._embedder = embedder

    async def search(self, query: str, top_k: int | None = None) -> list[Chunk]:
        k = top_k or settings.retrieval_top_k
        query_embedding = await self._embedder.embed_one(query)
        return await self._store.search(query_embedding, k)
