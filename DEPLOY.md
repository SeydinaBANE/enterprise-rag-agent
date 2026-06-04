# Deployment Guide

## Environments

| Env | Branch | Image Tag | Trigger |
|---|---|---|---|
| local | any | `local` | `make docker-build` |
| staging | `feat/*` | `sha-<commit>` | manual |
| production | `main` | `latest` + `sha-<hash>` | auto on merge |

## Production Deploy (Docker)

```bash
docker pull ghcr.io/<user>/enterprise-rag-agent:latest

docker run -d \
  --name rag-agent \
  --env-file .env.prod \
  -p 8000:8000 \
  --restart unless-stopped \
  ghcr.io/<user>/enterprise-rag-agent:latest
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|---|
| `OPENROUTER_API_KEY` | yes | — | OpenRouter API key |
| `API_KEY` | yes | — | Secret for `X-API-Key` header |
| `CHROMA_HOST` | no | `localhost` | ChromaDB host |
| `CHROMA_PORT` | no | `8001` | ChromaDB port |
| `LLM_MODEL` | no | `openai/gpt-4o-mini` | Model identifier |
| `EMBEDDING_MODEL` | no | `openai/text-embedding-3-small` | Embedding model |
| `LLM_TIMEOUT` | no | `60` | LLM request timeout (seconds) |
| `LLM_MAX_RETRIES` | no | `2` | Max LLM retries with exponential backoff |
| `MAX_UPLOAD_SIZE_MB` | no | `50` | Max file upload size (MB) |
| `LOG_LEVEL` | no | `info` | `debug`/`info`/`warning` |
| `MAX_CHUNK_SIZE` | no | `512` | Token chunk size for ingestion |
| `CHUNK_OVERLAP` | no | `50` | Token overlap between chunks |
| `RETRIEVAL_TOP_K` | no | `5` | Number of chunks retrieved per query |
| `POSTGRES_DSN` | no | — | Postgres DSN for persistent session storage (enables pool) |
| `POSTGRES_POOL_MIN` | no | `2` | Min Postgres pool connections |
| `POSTGRES_POOL_MAX` | no | `10` | Max Postgres pool connections |
| `ALLOWED_ORIGINS` | no | `["http://localhost:3000"]` | CORS allowed origins |
| `RATE_LIMIT_CHAT` | no | `20/minute` | Chat rate limit per IP |
| `RATE_LIMIT_INGEST` | no | `5/minute` | Ingest rate limit per IP |
| `ALLOWED_URL_DOMAINS` | no | `[]` | Restrict URL ingestion to specific domains (empty = all) |
| `TRUSTED_PROXIES` | no | `0` | Number of trusted reverse proxies |
| `WORKERS` | no | `1` | Uvicorn workers (set `4` in production) |

## GitHub Actions — Automated Release

On push to `main`:
1. CI must pass (lint + typecheck + test)
2. Docker image built (multi-stage)
3. Trivy scan — blocks on CRITICAL/HIGH CVEs
4. Image pushed to `ghcr.io/<user>/enterprise-rag-agent:latest` and `:sha-<hash>`

## Rollback

```bash
# Find a previous stable sha
docker image ls ghcr.io/<user>/enterprise-rag-agent

# Roll back
docker stop rag-agent && docker rm rag-agent
docker run -d --name rag-agent ... ghcr.io/<user>/enterprise-rag-agent:sha-<previous-sha>
```

## Health Check

```bash
curl http://localhost:8000/health
# {"status": "ok", "chromadb": "ok", "llm": "ok", "uptime_seconds": 3600}
```

## Infrastructure (Docker Compose)

| Service | Port | Purpose |
|---|---|---|
| `frontend` | 3000 | Next.js UI |
| `app` | 8000 | FastAPI application |
| `chromadb` | 8001 | Vector store |
| `postgres` | 5432 | Session storage |
| `prometheus` | 9090 | Metrics scraping |
| `grafana` | 3001 | Metrics dashboards (admin / admin) |

```bash
make docker-up    # start all
make docker-down  # stop all
```
