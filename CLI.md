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
      "score": 0.92
    }
  ],
  "session_id": "user-123",
  "used_retrieval": true,
  "latency_ms": 1240
}
```

**Errors**
| Status | Reason |
|---|---|
| `401` | Missing or invalid `X-API-Key` |
| `422` | Invalid request body |
| `429` | Rate limit exceeded |
| `500` | LLM or retrieval error |

---

### POST /documents/ingest

Upload a document to the knowledge base.

**File upload (multipart/form-data)**
```bash
curl -X POST http://localhost:8000/documents/ingest \
  -H "X-API-Key: your-key" \
  -F "file=@contract.pdf"
```

**URL ingestion (application/json)**
```bash
curl -X POST http://localhost:8000/documents/ingest \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/policy.html"}'
```

**Response**
```json
{
  "document_id": "contract-v2.pdf",
  "chunks_stored": 42,
  "status": "ok"
}
```

Supported formats: `.pdf`, `.txt`, HTTP/HTTPS URLs.

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
      "ingested_at": "2026-06-04T10:00:00Z"
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

| Command | Description |
|---|---|
| `make install` | Install deps + pre-commit hooks |
| `make run` | Start API (hot reload, port 8000) |
| `make docker-up` | Start all services |
| `make docker-down` | Stop all services |
| `make docker-build` | Build local Docker image |
| `make lint` | Run ruff linter |
| `make format` | Auto-format with ruff |
| `make typecheck` | Run mypy strict |
| `make security` | Run bandit SAST |
| `make test` | Run unit tests with coverage |
| `make test-integration` | Run integration tests |
| `make test-all` | Run all tests |
| `make check` | Run lint + typecheck + security + test |
| `make pre-commit-run` | Run all pre-commit hooks manually |

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

# 4. Start
make docker-up
make run
# → http://localhost:8000/docs
```
