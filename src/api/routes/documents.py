from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile

from src.api.middleware.auth import require_api_key
from src.api.middleware.ratelimit import limiter
from src.domain.config import settings
from src.domain.exceptions import EmbeddingError, UnsupportedSourceError, VectorStoreError
from src.domain.models import DocumentMeta, IngestRequest, IngestResponse
from src.observability.telemetry import ingest_requests_total

router = APIRouter()

_MAX_FILE_SIZE = settings.max_upload_size_mb * 1024 * 1024


@router.post(
    "/documents/ingest",
    response_model=IngestResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(settings.rate_limit_ingest)
async def ingest_file(request: Request, file: UploadFile) -> IngestResponse:
    pipeline = request.app.state.pipeline
    suffix = Path(file.filename or "upload").suffix or ".bin"

    data = await file.read()
    if len(data) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_upload_size_mb} MB limit",
        )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
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

    documents = []
    for doc_id, count, ingested_at_str in doc_list:
        if ingested_at_str:
            ingested_at = datetime.fromisoformat(ingested_at_str)
        else:
            ingested_at = datetime.utcnow()
        documents.append(DocumentMeta(id=doc_id, chunks=count, ingested_at=ingested_at))

    return {"documents": [d.model_dump() for d in documents], "total": len(documents)}
