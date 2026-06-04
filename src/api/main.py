from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.agent.graph import build_agent
from src.agent.memory import InMemorySessionStore
from src.agent.tools import RAGSearchTool
from src.api.middleware.logging import RequestLoggingMiddleware
from src.api.routes import chat, documents, health
from src.core.config import settings
from src.core.ports import ISessionStore
from src.infra.llm_client import LiteLLMClient
from src.infra.vector_store import ChromaVectorStore
from src.rag.embedder import Embedder
from src.rag.ingestion.pipeline import IngestPipeline
from src.rag.retriever import Retriever

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)


def _build_session_store() -> ISessionStore:
    if settings.postgres_dsn:
        from src.infra.postgres_session_store import PostgresSessionStore

        return PostgresSessionStore(settings.postgres_dsn)
    return InMemorySessionStore()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Enterprise RAG Agent",
        description="Production-grade agentic RAG system for enterprise knowledge management",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
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
