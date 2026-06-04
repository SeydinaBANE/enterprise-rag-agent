# RUN.md

How to run the Enterprise RAG Agent locally and in production.

---

## Prerequisites

- Python 3.12 (`uv` manages the virtualenv — install from https://docs.astral.sh/uv/)
- Docker & Docker Compose (for ChromaDB, Postgres, Prometheus, Grafana)
- An [OpenRouter](https://openrouter.ai) API key

---

## 1. Environment

```bash
cp .env.example .env
```

Mandatory fields in `.env`:

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter key (`sk-or-v1-...`) |
| `API_KEY` | Bearer token clients must send in `X-API-Key` |

Optional fields (all have defaults):

| Variable | Default | Description |
|---|---|---|
| `LLM_MODEL` | `openai/gpt-4o-mini` | Chat model via OpenRouter |
| `EMBEDDING_MODEL` | `openai/text-embedding-3-small` | Embedding model via OpenRouter |
| `CHROMA_HOST` | `localhost` | ChromaDB host |
| `CHROMA_PORT` | `8001` | ChromaDB port |
| `MAX_CHUNK_SIZE` | `512` | Tokens per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `RETRIEVAL_TOP_K` | `5` | Chunks returned per query |
| `POSTGRES_DSN` | _(unset)_ | If set, enables persistent sessions via Postgres; otherwise uses in-memory |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | _(unset)_ | OpenTelemetry collector endpoint |

---

## 2. Local development (fast path)

Runs the API with hot reload. ChromaDB must be available (start it via Docker or use the full stack below).

```bash
make install      # uv sync + pre-commit install
make docker-up    # starts ChromaDB, Postgres, Prometheus, Grafana
make run          # uvicorn on http://localhost:8000 with --reload
```

Stop the background services:

```bash
make docker-down
```

---

## 3. Full Docker Compose stack

Runs everything (app + all services) as containers. The app image is built from `Dockerfile`.

```bash
make docker-build                  # builds enterprise-rag-agent:local
docker compose up                  # foreground, all services
# or
docker compose up -d               # detached
docker compose logs -f app         # follow app logs
docker compose down -v             # stop and remove volumes
```

Port map:

| Service | Port |
|---|---|
| API | `http://localhost:8000` |
| ChromaDB | `http://localhost:8001` |
| Postgres | `localhost:5432` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` (admin / admin) |

> **Note**: in Compose mode `CHROMA_HOST=chromadb` and `POSTGRES_DSN` are injected automatically via the `environment` block — don't override them in `.env` unless you know what you're doing.

---

## 4. API usage

All data endpoints require the header `X-API-Key: <your API_KEY>`.

### Health check (no auth)

```bash
curl http://localhost:8000/health
# {"status":"ok","chromadb":"ok","llm":"ok","sessions":"ok","uptime_seconds":12}
```

### Ingest a file

```bash
curl -X POST http://localhost:8000/documents/ingest \
  -H "X-API-Key: change-me-in-production" \
  -F "file=@/path/to/document.pdf"
```

### Ingest a URL

```bash
curl -X POST http://localhost:8000/documents/ingest/url \
  -H "X-API-Key: change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

Supported sources: `.pdf`, `.txt`, `.md`, `.rst`, and any `http(s)://` URL.

### Chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "X-API-Key: change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"message": "What does the document say about X?", "session_id": "session-abc"}'
```

Response includes `answer`, `sources`, `used_retrieval`, and `latency_ms`. Pass the same `session_id` across turns to maintain conversation history (max 10 turns).

### List documents

```bash
curl http://localhost:8000/documents \
  -H "X-API-Key: change-me-in-production"
```

### Prometheus metrics (no auth)

```bash
curl http://localhost:8000/metrics
```

---

## 5. Interactive API docs

FastAPI's Swagger UI is available at `http://localhost:8000/docs` when the server is running.

---

## 6. Running tests

```bash
make test                  # unit tests only — no Docker required
make test-integration      # requires make docker-up first
make check                 # lint + typecheck + security + unit tests
```

Run a single test:

```bash
uv run pytest tests/unit/test_guardrails.py::test_check_input_valid -v
```
