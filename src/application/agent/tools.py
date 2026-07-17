from __future__ import annotations

from dataclasses import dataclass

from src.application.rag.embedder import Embedder
from src.domain.models import Chunk
from src.ports.outbound import IVectorStore


@dataclass
class SearchResult:
    chunks: list[Chunk]

    def format(self) -> str:
        if not self.chunks:
            return "No relevant documents found."
        parts = [f"[Source: {c.source}]\n{c.content}" for c in self.chunks]
        return "\n\n---\n\n".join(parts)


class RAGSearchTool:
    name = "rag_search"
    description = "Search the knowledge base for relevant document chunks."

    def __init__(self, vector_store: IVectorStore, embedder: Embedder) -> None:
        self._store = vector_store
        self._embedder = embedder

    async def run(self, query: str, top_k: int = 5) -> SearchResult:
        embedding = await self._embedder.embed_one(query)
        chunks = await self._store.search(embedding, top_k)
        return SearchResult(chunks=chunks)
