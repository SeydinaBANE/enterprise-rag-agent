from __future__ import annotations

from src.core.models import Chunk
from src.core.ports import IVectorStore
from src.rag.embedder import Embedder
from src.rag.ingestion.loader import get_loader
from src.rag.ingestion.splitter import TextSplitter


class IngestPipeline:
    def __init__(
        self,
        vector_store: IVectorStore,
        embedder: Embedder,
        splitter: TextSplitter | None = None,
    ) -> None:
        self._store = vector_store
        self._embedder = embedder
        self._splitter = splitter or TextSplitter()

    async def run(self, source: str) -> list[Chunk]:
        loader = get_loader(source)
        documents = await loader.load(source)

        all_chunks: list[Chunk] = []
        for document in documents:
            all_chunks.extend(self._splitter.split(document))

        if not all_chunks:
            return []

        texts = [c.content for c in all_chunks]
        embeddings = await self._embedder.embed(texts)

        for chunk, embedding in zip(all_chunks, embeddings, strict=True):
            chunk.embedding = embedding

        await self._store.add_chunks(all_chunks)
        return all_chunks
