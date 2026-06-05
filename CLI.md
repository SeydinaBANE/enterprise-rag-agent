# CLI & API Reference

## REST API

**Base URL**: `http://localhost:8000`
**Auth**: All endpoints except `/health` and `/metrics` require `X-API-Key: <your-api-key>` header.

---

### POST /chat

Ask the agent a question. The agent autonomously decides whether to use RAG retrieval.

**Request**
```json
{
  "message": "What does the contract say about termination clauses?",
  "session_id": "user-123"
}
```

**Response**
```json
{
  "answer": "According to section 4.2, termination requires 30 days written notice...",
  "sources": [
    {
      "document_id": "contract-v2.pdf",
      "chunk": "...termination requires 30 days written notice...",
      "score": 0.0
    }
  ],
  "session_id": "user-123",
  "used_retrieval": true,
  "latency_ms": 1240.0
}
```

**Errors**
| Status | Reason |
|---|---|
| `401` | Missing or invalid `X-API-Key` |
| `422` | Input too long, prompt injection detected, or invalid request body |
| `429` | Rate limit exceeded (default 20/min per IP) |
| `500` | LLM or storage error |

---

### POST /documents/ingest

Upload a file to the knowledge base (multipart/form-data). Max size: `MAX_UPLOAD_SIZE_MB` (default 50 MB).

```bash
curl -X POST http://localhost:8000/documents/ingest \
  -H "X-API-Key: your-key" \
  -F "file=@contract.pdf"
```

**Response**
```json
{
  "document_id": "contract.pdf",
  "chunks_stored": 42
}
```

Supported formats: `.pdf`, `.txt`, `.md`, `.rst`.

**Errors**
| Status | Reason |
|---|---|
| `401` | Missing or invalid `X-API-Key` |
| `413` | File exceeds `MAX_UPLOAD_SIZE_MB` |
| `422` | Unsupported file format |
| `429` | Rate limit exceeded (default 5/min per IP) |
| `500` | Storage error |
| `502` | Embedding service error |

---

### POST /documents/ingest/url

Ingest a web page or remote document by URL.

```bash
curl -X POST http://localhost:8000/documents/ingest/url \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/policy.html"}'
```

**Response**
```json
{
  "document_id": "https://example.com/policy.html",
  "chunks_stored": 17
}
```

The SSRF guard blocks private IP ranges. If `ALLOWED_URL_DOMAINS` is set, only matching hostnames are permitted.

**Errors**
| Status | Reason |
|---|---|
| `401` | Missing or invalid `X-API-Key` |
| `422` | Private IP / blocked domain (SSRF guard) or unsupported URL |
| `429` | Rate limit exceeded (default 5/min per IP) |
| `500` | Storage error |
| `502` | Embedding service error |

---

### GET /documents

List all ingested documents.

```bash
curl http://localhost:8000/documents \
  -H "X-API-Key: your-key"
```

**Response**
```json
{
  "documents": [
    {
      "id": "contract-v2.pdf",
      "chunks": 42,
      "ingested_at": "2026-06-04T10:00:00"
    }
  ],
  "total": 1
}
```

---

### GET /health

Check system health. No auth required.

```bash
curl http://localhost:8000/health
```

**Response**
```json
{
  "status": "ok",
  "chromadb": "ok",
  "llm": "ok",
  "sessions": "ok",
  "uptime_seconds": 3600
}
```

`status` is `"degraded"` if any dependency is unreachable.

---

### GET /metrics

Prometheus metrics. No auth required.

```bash
curl http://localhost:8000/metrics
```

Returns plain text in Prometheus exposition format. Key metrics:

| Metric | Type | Description |
|---|---|---|
| `chat_requests_total` | Counter | Total chat requests by status |
| `ingest_requests_total` | Counter | Total ingest requests by status |
| `retrieval_latency_seconds` | Histogram | Time spent on RAG retrieval |
| `llm_latency_seconds` | Histogram | Time spent on LLM generation |
| `active_sessions` | Gauge | Current active sessions |

---

## Makefile Commands

### Backend

| Command | Description |
|---|---|
| `make install` | Install deps + pre-commit hooks |
| `make run` | Start API (hot reload, port 8000) |
| `make docker-up` | Start all services |
| `make docker-down` | Stop all services |
| `make docker-build` | Build standalone Docker image (`enterprise-rag-agent:local`) |
| `make lint` | ruff linter |
| `make format` | Auto-format with ruff |
| `make format-check` | Check formatting without modifying files |
| `make typecheck` | mypy strict |
| `make security` | bandit SAST |
| `make test` | Unit tests with coverage (≥ 80%) |
| `make test-integration` | Integration tests (requires `make docker-up`) |
| `make test-all` | All tests with coverage (≥ 80%) |
| `make check` | lint + format-check + typecheck + security + test |
| `make pre-commit-run` | Run all pre-commit hooks manually |

### Frontend

| Command | Description |
|---|---|
| `make frontend-install` | `npm ci` in `frontend/` |
| `make frontend-dev` | Dev server on `localhost:3000` |
| `make frontend-build` | Production build |
| `make frontend-lint` | ESLint |
| `make frontend-typecheck` | `tsc --noEmit` |

## Environment Setup (one-time)

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and install
git clone https://github.com/<user>/enterprise-rag-agent
cd enterprise-rag-agent
make install

# 3. Configure
cp .env.example .env
# Set OPENROUTER_API_KEY and API_KEY in .env

# 4. Start services (ChromaDB, Postgres, Prometheus, frontend:3000, Grafana:3001)
make docker-up
docker compose stop app   # free port 8000

# 5. Start API with hot reload
make run
# → http://localhost:8000/docs
```
