# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
make install              # uv sync + pre-commit install

# Development
make run                  # FastAPI on localhost:8000 (hot reload) — stop app container first if running
make docker-up            # ChromaDB + Postgres + Prometheus + Grafana (detached)
make docker-down

# Quality (all must pass before committing)
make lint                 # ruff check src/ tests/
make format               # ruff format src/ tests/
make typecheck            # mypy src/ (strict)
make security             # bandit -r src/ -ll
make test                 # pytest tests/unit/ --cov-fail-under=80 (fast, no Docker)
make test-integration     # pytest tests/integration/ -m integration (requires make docker-up first)
make check                # lint + typecheck + security + test

# Single test
uv run pytest tests/unit/test_guardrails.py::test_check_input_valid -v

# Docker
make docker-build                    # builds enterprise-rag-agent:local (standalone image, not used by Compose)
docker compose up -d --build app     # rebuild + restart the Compose app container
```

Environment: copy `.env.example` → `.env`, set `OPENROUTER_API_KEY` and `API_KEY`.
Tests override env vars inline — no `.env` needed to run `make test`.

## Architecture

**Clean Architecture in 4 layers** — dependencies only flow inward:

```
API (FastAPI) → Agent → Domain (core/) ← Infra (infra/)
                  ↓
               RAG pipeline
```

### Domain layer (`src/core/`) — zero external dependencies

- `config.py`: `Settings` (pydantic-settings). Instantiated as `settings` singleton at import time. All modules read from `settings`, never from `os.environ` directly. Key production fields: `allowed_origins` (list, default `["http://localhost:3000"]`), `rate_limit_chat` (default `"20/minute"`), `rate_limit_ingest` (default `"5/minute"`), `workers` (default `1`), `llm_timeout` (default `60`), `llm_max_retries` (default `2`), `max_upload_size_mb` (default `50`), `postgres_pool_min` (default `2`), `postgres_pool_max` (default `10`), `trusted_proxies` (default `0`), `allowed_url_domains` (default `[]`).
- `ports.py`: Four ABCs — `ILLMClient`, `IVectorStore`, `IDocumentLoader`, `ISessionStore`. The entire codebase depends on these, never on concrete implementations.
- `models.py`: All Pydantic models. `AgentState` is a `TypedDict` (mutable dict passed through agent steps).
- `exceptions.py`: `GuardrailViolation`, `LLMError`, `EmbeddingError`, `VectorStoreError`, `DocumentNotFoundError`, `UnsupportedSourceError` — raised in domain/infra, caught in API routes.

### Infrastructure adapters (`src/infra/`)

- `LiteLLMClient` implements `ILLMClient` via OpenRouter (`openrouter/<model>`). The model prefix is added automatically — don't pass it in call sites. Features configurable `llm_timeout` and `llm_max_retries` with exponential backoff. The healthcheck uses a lightweight HEAD request to the OpenRouter auth endpoint instead of a paid `acompletion("ping")`.
- `ChromaVectorStore` implements `IVectorStore`. **Critical**: `chromadb.AsyncHttpClient()` must be awaited (it's an async factory). The client is lazily initialized on first use via `_get_client()`. On ingest, `_check_dimension()` guards against embedding dimension mismatch. The chromadb stubs expect numpy arrays; `list[list[float]]` is passed with `# type: ignore[arg-type]` — this is intentional and correct at runtime. `list_documents()` returns `list[tuple[str, int, str]]` (document_id, chunk_count, ingested_at_iso).
- `ISessionStore` has two backends: `InMemorySessionStore` (default, in `src/agent/memory.py`) and `PostgresSessionStore` (used when `settings.postgres_dsn` is set). `_build_session_store()` in `main.py` selects between them at startup.

### RAG pipeline (`src/rag/`)

Ingestion flow: `get_loader(source)` → `IDocumentLoader.load()` → `TextSplitter.split()` → `Embedder.embed()` → `IVectorStore.add_chunks()`. `get_loader()` dispatches on source: URLs → `URLLoader` (httpx + BeautifulSoup), `.pdf` → `PDFLoader` (pypdf), `.txt/.md/.rst` → `TextLoader`. URLs go through an SSRF guard (`_validate_url()`) that blocks private IPs via DNS resolution and supports an optional domain allowlist (`ALLOWED_URL_DOMAINS`). httpx timeout is `Timeout(15.0, connect=5.0)`. Add new formats by implementing `IDocumentLoader` in `loader.py` and registering in `get_loader()`.

### Agent (`src/agent/`)

`AgentGraph.invoke()` runs three async steps sequentially on an `AgentState` dict:
1. `_route()` — LLM classifies query as RAG or DIRECT
2. `_rag_search()` — only if RAG; embeds query, retrieves chunks from vector store
3. `_generate()` — LLM generates answer with conversation history + retrieved context

Session memory lives in `InMemorySessionStore` (in-process dict of `ConversationMemory`, max 10 turns). All services are instantiated once in `create_app()` and stored on `app.state`.

### Guardrails (`src/guardrails/filters.py`)

`check_input()` enforces a 4096-char limit and blocks prompt-injection patterns. `check_output()` enforces an 8192-char limit and calls `redact_pii()`, which replaces SSNs, credit card numbers, emails, and phone numbers with `[REDACTED]`.

### Observability (`src/observability/telemetry.py`)

Prometheus metrics module-level singletons: `chat_requests_total` (Counter, labelled `status`), `ingest_requests_total`, `retrieval_latency_seconds` (Histogram), `llm_latency_seconds` (Histogram), `active_sessions` (Gauge). Import these directly in routes/tools — never create new metric instances.

### API (`src/api/`)

Routes access services via `request.app.state.<service>`. Auth is a FastAPI `Depends` on all data endpoints — never on `/health` or `/metrics`. Guardrail `check_input()` is called before agent invocation; `check_output()` redacts PII from the LLM response before returning.

**Lifespan** (`main.py`): on startup, checks ChromaDB and Postgres reachability before accepting traffic (fail-fast). On shutdown, closes the `PostgresSessionStore` connection pool cleanly.

**Rate limiting** (`src/api/middleware/ratelimit.py`): module-level `slowapi.Limiter` singleton. IP detection uses X-Forwarded-For → X-Real-IP → client.host fallback (proxy-aware). Applied with `@limiter.limit(settings.rate_limit_chat)` on `/chat` (default 20/min) and `@limiter.limit(settings.rate_limit_ingest)` on ingest endpoints (default 5/min). The `request: Request` parameter must be the first argument of any rate-limited route function.

**Global exception handler**: unhandled exceptions return `{"detail": "Internal server error", "request_id": "<uuid>"}` (JSON 500) instead of the default HTML Starlette error page. The `request_id` is set by `RequestLoggingMiddleware` on `request.state.request_id`.

## Testing patterns

Unit tests mock at the interface boundary using `MockLLMClient`, `MockVectorStore`, and `MockSessionStore` from `tests/conftest.py` — these are plain classes with `AsyncMock` attributes (not ABC subclasses). Set `side_effect` on `mock_llm.complete` when a test calls it multiple times (e.g., route call then generate call). Default embed return is `[[0.1] * 384]`.

Integration tests require ChromaDB via `make docker-up`. Mark with `@pytest.mark.integration` and import infra adapters inside the fixture, not at module level.

## Key constraints

- `src/core/` must remain free of external library imports.
- All config values come from `settings` (never hardcode or read env vars directly).
- Business exceptions (`GuardrailViolation`, `LLMError`, `EmbeddingError`, `VectorStoreError`) are raised in domain/infra, caught in API routes: `EmbeddingError` → 502, `VectorStoreError` → 500, `LLMError` → 500, `GuardrailViolation` → 422.
- Commit format: `<type>(<scope>): <description>`.
- **ChromaDB collection dimension**: the `documents` collection is created on first ingest and its embedding dimension is fixed. If the embedding model changes or tests (mock 384-dim) run before production (1536-dim), delete the collection before re-ingesting: `curl -X DELETE http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections/documents`. The `_check_dimension()` guard now catches mismatches at ingest time with a clear error message.
- **SSRF guard**: URL ingestion resolves the hostname via `socket.getaddrinfo()` and blocks private IP ranges (10.x, 172.16-31.x, 192.168.x, 127.x, 169.254.x, ::1, fc00::/7). Set `ALLOWED_URL_DOMAINS` to restrict which domains are allowed.
- **Upload limit**: file uploads are limited to `MAX_UPLOAD_SIZE_MB` (default 50 MB). Exceeding returns HTTP 413.
