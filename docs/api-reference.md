# API Reference

Full interactive documentation available at `http://localhost:8000/docs` (Swagger UI)
and `http://localhost:8000/redoc` (ReDoc) when the server is running.

## Authentication

All endpoints except `/health` and `/metrics` require the `X-API-Key` header:

```
X-API-Key: your-api-key
```

The key is configured via the `API_KEY` environment variable.

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/chat` | yes | Agentic chat with RAG |
| `POST` | `/documents/ingest` | yes | Ingest a document |
| `GET` | `/documents` | yes | List ingested documents |
| `GET` | `/health` | no | Health check |
| `GET` | `/metrics` | no | Prometheus metrics |

See [CLI.md](../CLI.md) for full request/response examples with `curl`.

## Error Responses

All errors follow the standard FastAPI error format:

```json
{
  "detail": "human-readable error message"
}
```

| Status | Meaning |
|---|---|
| `401` | Missing or invalid API key |
| `422` | Validation error (bad request body) |
| `429` | Rate limit exceeded |
| `500` | Internal server error (LLM or retrieval failure) |

## OpenAPI Spec

Export the full spec:

```bash
curl http://localhost:8000/openapi.json > openapi.json
```
