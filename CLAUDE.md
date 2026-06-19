# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
make install              # uv sync + pre-commit install

# Development
make run                  # FastAPI on localhost:8000 (hot reload) — stop app container first if running
make docker-up            # all services: ChromaDB:8001, Postgres:5432, Prometheus:9090, frontend:3000, Grafana:3001 (detached)
make docker-down

# Frontend (Next.js 16)
make frontend-install     # npm ci
make frontend-dev         # dev server on localhost:3000
make frontend-build       # production build
make frontend-lint        # eslint
make frontend-typecheck   # tsc --noEmit

# Quality (all must pass before committing)
make lint                 # ruff check src/ tests/
make format               # ruff format src/ tests/
make format-check         # ruff format --check (non-destructive, used by make check)
make typecheck            # mypy src/ (strict)
make security             # bandit -r src/ -ll
make test                 # pytest tests/unit/ --cov-fail-under=80 (fast, no Docker)
make test-integration     # pytest tests/integration/ -m integration (requires Docker)
make test-all             # unit + integration tests together
make check                # lint + format-check + typecheck + security + test
make pre-commit-run       # run all pre-commit hooks against all files

# Single test
uv run pytest tests/unit/test_guardrails.py::test_check_input_valid -v

# Docker
make docker-build                    # builds enterprise-rag-agent:local (standalone image, not used by Compose)
docker compose up -d --build app     # rebuild + restart the Compose app container
```

Environment: copy `.env.example` → `.env`, set `OPENROUTER_API_KEY` and `API_KEY`.
For the frontend, copy `frontend/.env.local.example` → `frontend/.env.local` (sets `NEXT_PUBLIC_API_URL`).
Tests override env vars inline — no `.env` needed to run `make test`.
Python 3.12 required (`requires-python = ">=3.12"`). Line length is **100** chars (ruff); formatters will reject lines over this.

**Docker port conflict**: `make docker-up` starts an app container on :8000. Always run `docker compose stop app` before `make run`, or the hot-reload server will fail to bind.

## Architecture

**Clean Architecture in 4 layers** — dependencies only flow inward:

```
API (FastAPI) → Agent → Domain (core/) ← Infra (infra/)
                  ↓
               RAG pipeline
```

### Domain layer (`src/core/`) — zero external dependencies

- `config.py`: `Settings` (pydantic-settings). Instantiated as `settings` singleton at import time. All modules read from `settings`, never from `os.environ` directly. Key fields: `llm_model` (default `"openai/gpt-4o-mini"`), `embedding_model` (default `"openai/text-embedding-3-small"`), `retrieval_top_k` (default `5`), `max_chunk_size` (default `512`), `chunk_overlap` (default `50`), `allowed_origins` (list, default `["http://localhost:3000"]`), `rate_limit_chat` (default `"20/minute"`), `rate_limit_ingest` (default `"5/minute"`), `workers` (default `1`), `llm_timeout` (default `60`), `llm_max_retries` (default `2`), `max_upload_size_mb` (default `50`), `postgres_pool_min` (default `2`), `postgres_pool_max` (default `10`), `trusted_proxies` (default `0`), `allowed_url_domains` (default `""`, comma-separated string of allowed hostnames), `chroma_mode` (default `"http"`, set to `"embedded"` for in-process ChromaDB), `chroma_data_path` (default `"/data/chroma"`, used only in embedded mode), `app_env` (default `"development"`).
- `ports.py`: Four ABCs — `ILLMClient`, `IVectorStore`, `IDocumentLoader`, `ISessionStore`. The entire codebase depends on these, never on concrete implementations.
- `models.py`: All Pydantic models. `AgentState` is a `TypedDict` (mutable dict passed through agent steps).
- `exceptions.py`: `GuardrailViolation`, `LLMError`, `EmbeddingError`, `VectorStoreError`, `DocumentNotFoundError`, `UnsupportedSourceError` — raised in domain/infra, caught in API routes.

### Infrastructure adapters (`src/infra/`)

- `LiteLLMClient` implements `ILLMClient` via OpenRouter (`openrouter/<model>`). The model prefix is added automatically — don't pass it in call sites. Features configurable `llm_timeout` and `llm_max_retries` with exponential backoff. The healthcheck uses a lightweight HEAD request to the OpenRouter auth endpoint instead of a paid `acompletion("ping")`.
- `ChromaVectorStore` implements `IVectorStore`. The client is lazily initialized on first use via `_get_client()`, which branches on `settings.chroma_mode`: `"http"` (default) awaits `chromadb.AsyncHttpClient()` against `chroma_host:chroma_port`; `"embedded"` awaits `chromadb.AsyncPersistentClient(path=chroma_data_path)` for an in-process store (no separate ChromaDB service — used by the Fly.io free-tier deployment). **Critical**: both factories are async and must be awaited. On ingest, `_check_dimension()` guards against embedding dimension mismatch. The chromadb stubs expect numpy arrays; `list[list[float]]` is passed with `# type: ignore[arg-type]` — this is intentional and correct at runtime. `list_documents()` returns `list[tuple[str, int, str]]` (document_id, chunk_count, ingested_at_iso).
- `ISessionStore` has two backends: `InMemorySessionStore` (default, in `src/agent/memory.py`) and `PostgresSessionStore` (used when `settings.postgres_dsn` is set). `_build_session_store()` in `main.py` selects between them at startup.

### RAG pipeline (`src/rag/`)

Ingestion flow: `get_loader(source)` → `IDocumentLoader.load()` → `TextSplitter.split()` → `Embedder.embed()` → `IVectorStore.add_chunks()`. The ingestion components live in `src/rag/ingestion/` (`loader.py`, `splitter.py`, `pipeline.py`). `get_loader()` dispatches on source: URLs → `URLLoader` (httpx + BeautifulSoup), `.pdf` → `PDFLoader` (pypdf), `.txt/.md/.rst` → `TextLoader`. URLs go through an SSRF guard (`_validate_url()`) that blocks private IPs via DNS resolution and supports an optional domain allowlist (`ALLOWED_URL_DOMAINS`). httpx timeout is `Timeout(15.0, connect=5.0)`. Add new formats by implementing `IDocumentLoader` in `loader.py` and registering in `get_loader()`.

### Agent (`src/agent/`)

`AgentGraph` (`graph.py`) is a **plain procedural class — not a LangGraph StateGraph** (LangGraph is a dependency but unused for orchestration). `AgentGraph.invoke()` runs three async steps sequentially on an `AgentState` dict:
1. `_route()` — LLM classifies query as RAG or DIRECT
2. `_rag_search()` — only if RAG; delegates to `RAGSearchTool` (`tools.py`), which embeds the query and calls `IVectorStore.search()`
3. `_generate()` — LLM generates answer with conversation history + retrieved context

**`RAGSearchTool` vs `Retriever`**: both wrap `IVectorStore` + `Embedder`, but serve different callers. `RAGSearchTool` (in `src/agent/tools.py`) is the agent's search interface and returns a `SearchResult` with formatted text. `Retriever` (in `src/rag/retriever.py`) is used by API route handlers for document lookup and returns raw `Chunk` lists.

Session memory lives in `InMemorySessionStore` (in-process dict of `ConversationMemory`, max 10 turns). All services are instantiated once in `create_app()` and stored on `app.state`: `llm_client`, `vector_store`, `embedder`, `retriever`, `session_store`, `pipeline`, `agent`.

### Guardrails (`src/guardrails/filters.py`)

`check_input()` enforces a 4096-char limit and blocks prompt-injection patterns. `check_output()` enforces an 8192-char limit and calls `redact_pii()`, which replaces SSNs, credit card numbers, emails, and phone numbers with `[REDACTED]`.

### Logging

Structured JSON logging via `structlog` with ISO timestamps. Use `structlog.get_logger()` — never `print` or `logging.getLogger`. Log entries include `request_id` (set by `RequestLoggingMiddleware`) for correlation. Log level is controlled by `LOG_LEVEL` env var (default `"info"`).

### Observability (`src/observability/telemetry.py`)

Prometheus metrics module-level singletons: `chat_requests_total` (Counter, labelled `status`), `ingest_requests_total`, `retrieval_latency_seconds` (Histogram), `llm_latency_seconds` (Histogram), `active_sessions` (Gauge). Import these directly in routes/tools — never create new metric instances.

### API (`src/api/`)

Routes access services via `request.app.state.<service>`. Auth (`X-API-Key` header) is a FastAPI `Depends` on all data endpoints — never on `/health` or `/metrics`. Guardrail `check_input()` is called before agent invocation; `check_output()` redacts PII from the LLM response before returning.

**Lifespan** (`main.py`): on startup, checks ChromaDB and Postgres reachability before accepting traffic (fail-fast). On shutdown, closes the `PostgresSessionStore` connection pool cleanly.

**Rate limiting** (`src/api/middleware/ratelimit.py`): module-level `slowapi.Limiter` singleton. IP detection uses X-Forwarded-For → X-Real-IP → client.host fallback (proxy-aware). Applied with `@limiter.limit(settings.rate_limit_chat)` on `/chat` (default 20/min) and `@limiter.limit(settings.rate_limit_ingest)` on ingest endpoints (default 5/min). The `request: Request` parameter must be the first argument of any rate-limited route function.

**Global exception handler**: unhandled exceptions return `{"detail": "Internal server error", "request_id": "<uuid>"}` (JSON 500) instead of the default HTML Starlette error page. The `request_id` is set by `RequestLoggingMiddleware` on `request.state.request_id`.

**API endpoints**:
| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/chat` | API key | rate-limited 20/min |
| POST | `/documents/ingest` | API key | multipart file upload, rate-limited 5/min |
| POST | `/documents/ingest/url` | API key | JSON `{url}`, rate-limited 5/min |
| GET | `/documents` | API key | |
| GET | `/health` | none | ChromaDB + Postgres reachability |
| GET | `/metrics` | none | Prometheus scrape target |

### Frontend (`frontend/`)

Next.js 16 + React 19 app. **Next.js 16 has breaking API changes from earlier versions** — before writing any Next.js-specific code, read the relevant guide in `node_modules/next/dist/docs/` and heed deprecation notices. Do not rely on pre-16 conventions.

Stack: TypeScript (strict), Tailwind CSS v4, Zustand v5 (client state in `lib/store/`), React Query v5 (server state in hooks), Radix UI primitives (`components/ui/`).

**Pages**: root `/` redirects to `/chat` (main chat UI), `/documents` (ingest + list), `/settings` (API key + URL config). Routes are under `app/`.

**Components**: `components/chat/` (ChatWindow, InputBar, MessageBubble, SourcePanel), `components/documents/` (DocumentTable, FileUpload, UrlIngest), `components/shared/` (ApiKeyGuard wraps pages that require auth; HealthBadge), `components/ui/` (Radix-based primitives).

**State management**: two Zustand stores — `lib/store/config.ts` (`useConfigStore`, persisted to localStorage, holds `apiKey` + `apiUrl`) and `lib/store/session.ts` (`useSessionStore`, in-memory, holds `sessionId` + `messages`). `ApiKeyGuard` redirects to `/settings` when `apiKey` is empty.

Custom hooks in `hooks/` (`useChat`, `useDocuments`, `useHealth`) own all API calls via domain-specific modules: `lib/api/chat.ts` (exports `postChat`) and `lib/api/documents.ts`. Both delegate to `apiFetch` in `lib/api/client.ts`, which reads `apiKey` and `apiUrl` from `useConfigStore.getState()` and sends `X-API-Key` on every request. `ApiError` (with `.status`) is the typed error class thrown on non-2xx responses.

## Testing patterns

Unit tests mock at the interface boundary using `MockLLMClient`, `MockVectorStore`, and `MockSessionStore` from `tests/conftest.py` — these are plain classes with `AsyncMock` attributes (not ABC subclasses). Set `side_effect` on `mock_llm.complete` when a test calls it multiple times (e.g., route call then generate call). Default embed return is `[[0.1] * 384]`.

`asyncio_mode = "auto"` is set in `pyproject.toml` — do **not** add `@pytest.mark.asyncio` to async tests; it causes a duplicate-mark error.

Integration tests only require ChromaDB. `docker-compose.test.yml` starts just ChromaDB (lighter than `make docker-up`) — run `docker compose -f docker-compose.test.yml up -d` before `make test-integration`. Mark integration tests with `@pytest.mark.integration` and import infra adapters inside the fixture, not at module level.

## Architectural decisions

`docs/adr/` has three decision records worth reading when their rationale matters:
- `001-langgraph.md` — LangGraph `StateGraph` was the intended approach; the implementation diverged to a plain class. LangGraph remains a declared dependency.
- `002-chromadb.md` — why ChromaDB over pgvector or Pinecone.
- `003-openrouter-litellm.md` — why OpenRouter via LiteLLM instead of direct provider SDKs.

## Deployment

`DEPLOY.md` is the source of truth; two cloud targets are configured:

- **Fly.io free-tier** (`fly.toml`): single FastAPI container with **embedded ChromaDB** (`CHROMA_MODE=embedded`) persisted to a Fly volume at `/data/chroma` — no separate vector-store service. Pairs with Supabase (Postgres) + Vercel (frontend). `auto_stop_machines` keeps cost near zero. Deploy: `fly launch --no-deploy` → `fly secrets set OPENROUTER_API_KEY=... API_KEY=... POSTGRES_DSN=...` → `fly deploy`.
- **Render** (`render.yaml` blueprint): three services — `rag-api` (Docker web), `chromadb` (private service + persistent disk, `CHROMA_MODE=http`), and managed `rag-postgres`. `sync:false` secrets (`OPENROUTER_API_KEY`, `API_KEY`, `ALLOWED_ORIGINS`) are set in the dashboard after first deploy.
- **Frontend** (`vercel.json`): `rootDirectory: frontend`, auto-detected Next.js. Set `NEXT_PUBLIC_API_URL` to the backend URL, and the backend's `ALLOWED_ORIGINS` to the Vercel URL.
- Both production targets set `TRUSTED_PROXIES=1` (one proxy hop). Fly.io also sets `APP_ENV=production` via `[env]`; `render.yaml` does **not** set `APP_ENV`, so the Render service falls back to the `app_env="development"` default — add it manually in the dashboard if any code depends on it. Prometheus/Grafana are local-only — use the platform's built-in metrics in production.

## Key constraints

- `src/core/` must remain free of external library imports.
- All config values come from `settings` (never hardcode or read env vars directly).
- Business exceptions are raised in domain/infra, caught in API routes: `EmbeddingError` → 502, `VectorStoreError` → 500, `LLMError` → 500, `GuardrailViolation` → 422, `UnsupportedSourceError` → 422.
- Commit format: `<type>(<scope>): <description>`. `.commitlintrc.yml` exists but is **not** enforced by pre-commit — validation is manual.
- **ChromaDB collection dimension**: the `documents` collection is created on first ingest and its embedding dimension is fixed. If the embedding model changes or tests (mock 384-dim) run before production (1536-dim), delete the collection before re-ingesting: `curl -X DELETE http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections/documents`. The `_check_dimension()` guard now catches mismatches at ingest time with a clear error message.
- **SSRF guard**: URL ingestion resolves the hostname via `socket.getaddrinfo()` and blocks private IP ranges (10.x, 172.16-31.x, 192.168.x, 127.x, 169.254.x, ::1, fc00::/7). `ALLOWED_URL_DOMAINS` is a comma-separated string (e.g. `"example.com,docs.internal"`) — when non-empty, only hostnames ending with one of these values are permitted.
- **Upload limit**: file uploads are limited to `MAX_UPLOAD_SIZE_MB` (default 50 MB). Exceeding returns HTTP 413.
