from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter()

_start_time = time.monotonic()


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    vector_store = request.app.state.vector_store
    llm_client = request.app.state.llm_client
    session_store = request.app.state.session_store

    chroma_ok = await vector_store.is_healthy()
    llm_ok = await llm_client.is_healthy()
    sessions_ok = await session_store.is_healthy()

    all_ok = chroma_ok and llm_ok and sessions_ok
    status = "ok" if all_ok else "degraded"

    return {
        "status": status,
        "chromadb": "ok" if chroma_ok else "error",
        "llm": "ok" if llm_ok else "error",
        "sessions": "ok" if sessions_ok else "error",
        "uptime_seconds": round(time.monotonic() - _start_time),
    }


@router.get("/metrics")
async def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
