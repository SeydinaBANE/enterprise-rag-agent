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
|---|---|---|---|
| `OPENROUTER_API_KEY` | yes | — | OpenRouter API key |
| `API_KEY` | yes | — | Secret for `X-API-Key` header |
| `CHROMA_HOST` | no | `localhost` | ChromaDB host |
| `CHROMA_PORT` | no | `8001` | ChromaDB port |
| `LLM_MODEL` | no | `openai/gpt-4o-mini` | Model identifier |
| `EMBEDDING_MODEL` | no | `openai/text-embedding-3-small` | Embedding model |
| `LOG_LEVEL` | no | `info` | `debug`/`info`/`warning` |
| `MAX_CHUNK_SIZE` | no | `512` | Token chunk size for ingestion |
| `CHUNK_OVERLAP` | no | `50` | Token overlap between chunks |
| `RETRIEVAL_TOP_K` | no | `5` | Number of chunks retrieved per query |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | no | — | OTLP endpoint for trace export |

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
| `app` | 8000 | FastAPI application |
| `chromadb` | 8001 | Vector store |
| `prometheus` | 9090 | Metrics scraping |
| `grafana` | 3000 | Metrics dashboards |

```bash
make docker-up    # start all
make docker-down  # stop all
```
