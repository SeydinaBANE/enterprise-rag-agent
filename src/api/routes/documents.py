from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile

from src.api.middleware.auth import require_api_key
from src.api.middleware.ratelimit import limiter
from src.core.config import settings
from src.core.exceptions import EmbeddingError, UnsupportedSourceError, VectorStoreError
from src.core.models import DocumentMeta, IngestRequest, IngestResponse
from src.observability.telemetry import ingest_requests_total

router = APIRouter()


@router.post(
    "/documents/ingest",
    response_model=IngestResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(settings.rate_limit_ingest)
async def ingest_file(request: Request, file: UploadFile) -> IngestResponse:
    pipeline = request.app.state.pipeline
    suffix = Path(file.filename or "upload").suffix or ".bin"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        chunks = await pipeline.run(tmp_path)
    except UnsupportedSourceError as exc:
        ingest_requests_total.labels(status="unsupported").inc()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EmbeddingError as exc:
        ingest_requests_total.labels(status="error").inc()
        raise HTTPException(status_code=502, detail="Embedding service error") from exc
    except VectorStoreError as exc:
        ingest_requests_total.labels(status="error").inc()
        raise HTTPException(status_code=500, detail="Storage error") from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    ingest_requests_total.labels(status="ok").inc()
    return IngestResponse(
        document_id=file.filename or "upload",
        chunks_stored=len(chunks),
    )


@router.post(
    "/documents/ingest/url",
    response_model=IngestResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(settings.rate_limit_ingest)
async def ingest_url(request: Request, body: IngestRequest) -> IngestResponse:
    pipeline = request.app.state.pipeline

    try:
        chunks = await pipeline.run(body.url)
    except UnsupportedSourceError as exc:
        ingest_requests_total.labels(status="unsupported").inc()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EmbeddingError as exc:
        ingest_requests_total.labels(status="error").inc()
        raise HTTPException(status_code=502, detail="Embedding service error") from exc
    except VectorStoreError as exc:
        ingest_requests_total.labels(status="error").inc()
        raise HTTPException(status_code=500, detail="Storage error") from exc

    ingest_requests_total.labels(status="ok").inc()
    return IngestResponse(document_id=body.url, chunks_stored=len(chunks))


@router.get(
    "/documents",
    dependencies=[Depends(require_api_key)],
)
async def list_documents(request: Request) -> dict[str, Any]:
    vector_store = request.app.state.vector_store

    try:
        doc_list = await vector_store.list_documents()
    except VectorStoreError as exc:
        raise HTTPException(status_code=500, detail="Storage error") from exc

    documents = [
        DocumentMeta(id=doc_id, chunks=count, ingested_at=datetime.utcnow())
        for doc_id, count in doc_list
    ]
    return {"documents": [d.model_dump() for d in documents], "total": len(documents)}
