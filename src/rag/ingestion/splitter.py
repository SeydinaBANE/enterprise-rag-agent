from __future__ import annotations

import uuid

from src.core.config import settings
from src.core.models import Chunk, Document


class TextSplitter:
    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        self._chunk_size = chunk_size or settings.max_chunk_size
        self._overlap = chunk_overlap or settings.chunk_overlap

    def split(self, document: Document) -> list[Chunk]:
        words = document.content.split()
        if not words:
            return []

        chunks: list[Chunk] = []
        start = 0
        while start < len(words):
            end = min(start + self._chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append(
                Chunk(
                    id=str(uuid.uuid4()),
                    document_id=document.id,
                    content=chunk_text,
                    source=document.source,
                )
            )
            if end == len(words):
                break
            start = end - self._overlap

        return chunks
