from __future__ import annotations

import os

import litellm

from src.core.config import settings
from src.core.exceptions import EmbeddingError, LLMError
from src.core.ports import ILLMClient


class LiteLLMClient(ILLMClient):
    def __init__(self) -> None:
        os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key
        litellm.api_base = "https://openrouter.ai/api/v1"

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> str:
        try:
            response = await litellm.acompletion(
                model=f"openrouter/{model or settings.llm_model}",
                messages=messages,
                api_key=settings.openrouter_api_key,
                api_base="https://openrouter.ai/api/v1",
            )
            content: str = response.choices[0].message.content or ""
            return content
        except Exception as exc:
            raise LLMError(str(exc)) from exc

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = await litellm.aembedding(
                model=f"openrouter/{settings.embedding_model}",
                input=texts,
                api_key=settings.openrouter_api_key,
                api_base="https://openrouter.ai/api/v1",
            )
            return [item["embedding"] for item in response.data]
        except Exception as exc:
            raise EmbeddingError(str(exc)) from exc

    async def is_healthy(self) -> bool:
        try:
            await self.complete([{"role": "user", "content": "ping"}])
            return True
        except LLMError:
            return False
