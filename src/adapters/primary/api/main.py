from __future__ import annotations

import traceback
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.adapters.primary.api.middleware.logging import RequestLoggingMiddleware
from src.adapters.primary.api.middleware.ratelimit import limiter
from src.adapters.primary.api.routes import chat, documents, health
from src.adapters.secondary.llm_client import LiteLLMClient
from src.adapters.secondary.postgres_session_store import PostgresSessionStore
from src.adapters.secondary.vector_store import ChromaVectorStore
from src.application.agent.graph import build_agent
from src.application.agent.memory import InMemorySessionStore
from src.application.agent.tools import RAGSearchTool
from src.application.rag.embedder import Embedder
from src.application.rag.ingestion.pipeline import IngestPipeline
from src.application.rag.retriever import Retriever
from src.domain.config import settings
from src.ports.outbound import ISessionStore

logger = structlog.get_logger()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)


def _build_session_store() -> ISessionStore:
    if settings.postgres_dsn:
        return PostgresSessionStore(settings.postgres_dsn)
    logger.warning(
        "No POSTGRES_DSN configured — using in-memory session store. "
        "Sessions will be lost on restart."
    )
    return InMemorySessionStore()


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    vector_store: ChromaVectorStore = app.state.vector_store
    session_store: ISessionStore = app.state.session_store

    if not await vector_store.is_healthy():
        if settings.chroma_mode == "embedded":
            raise RuntimeError(
                f"ChromaDB embedded client failed to initialise at {settings.chroma_data_path}"
            )
        raise RuntimeError(
            f"ChromaDB is not reachable at {settings.chroma_host}:{settings.chroma_port}"
        )

    if settings.postgres_dsn and not await session_store.is_healthy():
        raise RuntimeError("Postgres session store is not reachable at startup")

    logger.info("startup_complete", chroma_mode=settings.chroma_mode)
    yield

    if isinstance(session_store, PostgresSessionStore):
        await session_store.close()
        logger.info("postgres_pool_closed")


def create_app() -> FastAPI:
    _is_prod = settings.app_env == "production"
    app = FastAPI(
        title="Enterprise RAG Agent",
        description="Production-grade agentic RAG system for enterprise knowledge management",
        version="0.1.0",
        lifespan=_lifespan,
        docs_url=None if _is_prod else "/docs",
        redoc_url=None if _is_prod else "/redoc",
        openapi_url=None if _is_prod else "/openapi.json",
    )

    app.state.limiter = limiter
    # slowapi's handler has a slightly different signature than FastAPI expects
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    @app.exception_handler(Exception)
    async def _global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            "unhandled_exception",
            request_id=request_id,
            path=request.url.path,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
        allow_credentials=False,
    )
    app.add_middleware(RequestLoggingMiddleware)

    llm_client = LiteLLMClient()
    vector_store = ChromaVectorStore()
    embedder = Embedder(llm_client)
    retriever = Retriever(vector_store, embedder)
    session_store = _build_session_store()
    rag_tool = RAGSearchTool(vector_store, embedder)
    pipeline = IngestPipeline(vector_store, embedder)
    agent = build_agent(llm_client, rag_tool, session_store)

    app.state.llm_client = llm_client
    app.state.vector_store = vector_store
    app.state.embedder = embedder
    app.state.retriever = retriever
    app.state.session_store = session_store
    app.state.pipeline = pipeline
    app.state.agent = agent

    app.include_router(chat.router)
    app.include_router(documents.router)
    app.include_router(health.router)

    return app


app = create_app()
