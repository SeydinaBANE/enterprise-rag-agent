from __future__ import annotations

import pytest

from src.infra.llm_client import LiteLLMClient, _is_retryable


class _StatusError(Exception):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"status {status_code}")


def test_is_retryable_classifies_errors() -> None:
    assert _is_retryable(TimeoutError()) is True
    assert _is_retryable(_StatusError(429)) is True
    assert _is_retryable(_StatusError(503)) is True
    assert _is_retryable(_StatusError(401)) is False
    assert _is_retryable(_StatusError(400)) is False
    assert _is_retryable(ValueError("boom")) is False


@pytest.mark.asyncio
async def test_call_with_retry_skips_non_transient() -> None:
    client = LiteLLMClient()
    client._max_retries = 2
    calls = 0

    async def _failing() -> str:
        nonlocal calls
        calls += 1
        raise _StatusError(401)

    with pytest.raises(_StatusError):
        await client._call_with_retry(_failing)
    assert calls == 1


@pytest.mark.asyncio
async def test_call_with_retry_retries_transient_then_succeeds() -> None:
    client = LiteLLMClient()
    client._max_retries = 2
    calls = 0

    async def _flaky() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise _StatusError(503)
        return "ok"

    result = await client._call_with_retry(_flaky)
    assert result == "ok"
    assert calls == 2
