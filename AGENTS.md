# AGENTS.md — enterprise-rag-agent

## Commands

```bash
make install              # uv sync + pre-commit install
make run                  # uvicorn hot-reload on :8000 — stop `docker compose stop app` first
make docker-up            # chromadb + postgres + prometheus + grafana (detached)
make docker-down
make lint                 # ruff check src/ tests/
make format               # ruff format src/ tests/
make format-check         # ruff format --check (read-only, used in CI and make check)
make typecheck            # mypy src/ (strict)
make security             # bandit -r src/ -ll
make test                 # pytest tests/unit/ -v --cov-fail-under=80 (fast, no Docker)
make test-integration     # pytest tests/integration/ -m integration (requires `make docker-up`)
make check                # lint + format-check + typecheck + security + test (must all pass before commit)

# Frontend
make frontend-install     # cd frontend && npm ci
make frontend-dev         # cd frontend && npm run dev (localhost:3000)
make frontend-build       # cd frontend && npm run build
make frontend-lint        # cd frontend && npm run lint
make frontend-typecheck   # cd frontend && npx tsc --noEmit

# Single test
uv run pytest tests/unit/test_guardrails.py::test_check_input_valid -v

# Rebuild app container after code changes (NOT `make docker-build`)
docker compose up -d --build app
make docker-build         # produces standalone image enterprise-rag-agent:local (not used by Compose)
```

## Architecture

Hexagonal (ports & adapters) — deps flow inward toward `src/domain/` and `src/ports/`:

```
adapters/primary/api (FastAPI) → ports/inbound → application/ (agent, rag) → ports/outbound ← adapters/secondary
                                                        ↓
                                                    domain/
```

- **`src/domain/`** — ZERO external library imports (stdlib + pydantic ecosystem only). Contains `Settings` singleton (`pydantic_settings.BaseSettings`), Pydantic models, exceptions.
- **`src/ports/`** — `outbound.py` has the four driven ABCs (`ILLMClient`, `IVectorStore`, `IDocumentLoader`, `ISessionStore`); `inbound.py` has the driving ABCs (`IChatUseCase`, `IIngestUseCase`).
- **AgentGraph** (`src/application/agent/graph.py`, implements `IChatUseCase`) is a **procedural class** (not LangGraph StateGraph). Runs `_route → _rag_search → _generate` sequentially on an `AgentState` dict.
- **All config values** from `settings` — never `os.environ` directly.
- **Prometheus metrics** are module-level singletons in `src/observability/telemetry.py` — never create metric instances elsewhere.

## Key gotchas

- **`chromadb.AsyncHttpClient()` must be awaited** — it's an async factory. `ChromaVectorStore` lazily initializes via `_get_client()`.
- **`openrouter/` model prefix** is added automatically by `LiteLLMClient` — set `LLM_MODEL` to bare name (e.g. `openai/gpt-4o-mini`).
- **ChromaDB dimension is fixed on first ingest**. If the embedding model changes (e.g. mock 384-dim tests run before production 1536-dim), delete the collection:
  ```bash
  curl -X DELETE http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections/documents
  ```
- **Mock LLM default embed** returns `[[0.1] * 384]` — production is 1536-dim.
- **`side_effect` on `mock_llm.complete`** when the agent makes multiple LLM calls (route + generate). `return_value` for single-call routes.
- **Integration tests**: mark `@pytest.mark.integration`, import infra adapters **inside** the fixture (not at module level).
- **No commitlint in pre-commit** despite `.commitlintrc.yml` existing — commit message validation is manual.
- **Docker port conflict**: `make docker-up` starts an app container on :8000. Run `docker compose stop app` before `make run`.
- **Exception → HTTP mapping**: `EmbeddingError`→502, `VectorStoreError`→500, `LLMError`→500, `GuardrailViolation`→422, `UnsupportedSourceError`→422.
- **Rate-limited routes**: the `request: Request` parameter must be **first** in the function signature for slowapi to detect it.
- **Guardrails**: `filters.check_input()` before agent invocation; `filters.check_output()` redacts PII before returning.

## Testing

- Mock infrastructure in `tests/conftest.py`: `MockLLMClient`, `MockVectorStore`, `MockSessionStore` are plain classes with `AsyncMock` attributes (NOT ABC subclasses — Python requires abstract methods at class level).
- Tests override env vars inline — no `.env` needed for `make test`.
- **Never instantiate** `ChromaVectorStore` or `LiteLLMClient` in unit tests.

## Existing instruction sources

- `CLAUDE.md` — full project conventions, kept in sync with the codebase.
- `docs/adr/` — architecture decisions for LangGraph, ChromaDB, OpenRouter+litellm.
