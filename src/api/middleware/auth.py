from __future__ import annotations

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from src.core.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    request: Request,  # noqa: ARG001
    api_key: str | None = Security(_api_key_header),
) -> None:
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
