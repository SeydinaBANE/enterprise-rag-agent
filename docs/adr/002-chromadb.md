# ADR 002 — Use ChromaDB as Vector Store

**Date**: 2026-06-04
**Status**: Accepted

## Context

The RAG pipeline requires a vector store for embedding-based document retrieval.
The system must work locally for development and in Docker for production without paid accounts.

## Decision

Use **ChromaDB** in client mode (Docker) for production, embedded mode for tests.

## Rationale

| Criterion | ChromaDB | Pinecone | Qdrant |
|---|---|---|---|
| Local / offline | Yes (embedded) | No (cloud only) | Yes (Docker) |
| Paid account required | No | Yes | No |
| Docker image available | Yes | N/A | Yes |
| Python async client | Yes (`AsyncClient`) | Yes | Yes |
| MMR reranking | Via LangChain wrapper | No | Built-in |
| Demo friendliness | High | Low | Medium |

ChromaDB's embedded mode enables fast unit tests without any Docker dependency.
The async HTTP client is used in production (Docker service on port 8001).

## Consequences

- `src/infra/vector_store.py` implements `IVectorStore` using `chromadb.AsyncHttpClient`
- Unit tests use `chromadb.EphemeralClient()` via the mock fixture in `tests/conftest.py`
- Integration tests use the real ChromaDB Docker service
- Switching to Qdrant requires only a new `IVectorStore` implementation in `src/infra/`
