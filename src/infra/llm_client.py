from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx
import litellm

from src.core.config import settings
from src.core.exceptions import EmbeddingError, LLMError
from src.core.ports import ILLMClient

_T = TypeVar("_T")

logger = logging.getLogger(__name__)


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, TimeoutError | httpx.TimeoutException | httpx.TransportError):
        return True
    status = getattr(exc, "status_code", None)
    return isinstance(status, int) and (status == 429 or status >= 500)


class LiteLLMClient(ILLMClient):
    def __init__(self) -> None:
        litellm.api_base = "https://openrouter.ai/api/v1"
        self._timeout = settings.llm_timeout
        self._max_retries = settings.llm_max_retries

    async def _call_with_retry(
        self,
        call: Callable[..., Awaitable[_T]],
        *args: object,
        **kwargs: object,
    ) -> _T:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await asyncio.wait_for(call(*args, **kwargs), timeout=self._timeout)
            except Exception as exc:
                last_exc = exc
                if attempt < self._max_retries and _is_retryable(exc):
                    wait = 0.5 * (2**attempt)
                    logger.warning(
                        "llm_retry attempt=%d wait=%.1f error=%s", attempt + 1, wait, str(exc)
                    )
                    await asyncio.sleep(wait)
                else:
                    break
        assert last_exc is not None
        raise last_exc

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> str:
        try:
            response = await self._call_with_retry(
                litellm.acompletion,
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
            response = await self._call_with_retry(
                litellm.aembedding,
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
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.head(
                    "https://openrouter.ai/api/v1/auth/key",
                    headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                )
                return resp.status_code == 200
        except Exception:
            return False
