from __future__ import annotations

from src.core.config import settings
from src.core.models import Chunk
from src.core.ports import IVectorStore
from src.rag.embedder import Embedder


class Retriever:
    def __init__(self, vector_store: IVectorStore, embedder: Embedder) -> None:
        self._store = vector_store
        self._embedder = embedder

    async def search(self, query: str, top_k: int | None = None) -> list[Chunk]:
        k = top_k or settings.retrieval_top_k
        query_embedding = await self._embedder.embed_one(query)
        return await self._store.search(query_embedding, k)
