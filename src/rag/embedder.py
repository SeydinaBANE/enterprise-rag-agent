from __future__ import annotations

from src.core.exceptions import EmbeddingError
from src.core.ports import ILLMClient


class Embedder:
    def __init__(self, llm_client: ILLMClient) -> None:
        self._client = llm_client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await self._client.embed(texts)

    async def embed_one(self, text: str) -> list[float]:
        results = await self.embed([text])
        if not results:
            raise EmbeddingError("No embedding returned for input text")
        return results[0]
