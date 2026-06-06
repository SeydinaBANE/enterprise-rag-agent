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

## Render + Vercel (Cloud)

### Architecture

```
Vercel (frontend, Next.js)
  └─► Render Web Service — rag-api (FastAPI, Docker)
          ├─► Render Private Service — chromadb (persistent disk)
          └─► Render Managed PostgreSQL — rag-postgres
```

Prometheus/Grafana are local-only — use Render's built-in metrics dashboard in production.

### First deploy — Render

1. Push this repo to GitHub.
2. On [render.com](https://render.com) → **New** → **Blueprint** → select this repo.
   Render reads `render.yaml` and creates all three services automatically.
3. After the first deploy, set the two secrets in the **rag-api** service environment:
   | Key | Value |
   |-----|-------|
   | `OPENROUTER_API_KEY` | your OpenRouter key |
   | `API_KEY` | a strong random secret |
   | `ALLOWED_ORIGINS` | your Vercel URL (e.g. `["https://your-app.vercel.app"]`) |
4. **Trigger a redeploy** of `rag-api` after setting the secrets.

Note on ChromaDB: the first request after a cold start will be slow while the private service initialises. The persistent disk at `/chroma/chroma` survives deploys.

### First deploy — Vercel

1. On [vercel.com](https://vercel.com) → **New Project** → import this repo.
   Vercel reads `vercel.json` → `rootDirectory: frontend` and auto-detects Next.js.
2. Set the environment variable:
   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | your Render service URL (e.g. `https://rag-api.onrender.com`) |
3. Deploy.

### Continuous deployment

Both platforms redeploy automatically on push to `main` once connected to the repo.

### Costs (approximate)

| Service | Plan | $/month |
|---------|------|---------|
| Render Web Service (rag-api) | Starter | $7 |
| Render Private Service (chromadb) | Starter | $7 |
| Render Managed PostgreSQL | Free | $0 |
| Render Persistent Disk (10 GB) | — | $2.50 |
| Vercel (frontend) | Hobby | $0 |
| **Total** | | **~$16.50** |

### Troubleshooting

**`CHROMA_HOST` unreachable** — the `chromadb` private service takes ~2 min to start on first deploy. Check its logs in the Render dashboard; the `rag-api` lifespan check will retry.

**`POSTGRES_DSN` format** — Render's `internalConnectionString` uses `postgresql://` which psycopg3 requires. If you manually set `POSTGRES_DSN`, use `postgresql://` not `postgres://`.

**Rate limiting off** — `TRUSTED_PROXIES=1` is set in `render.yaml` so `X-Forwarded-For` from Render's proxy is trusted for accurate IP detection.

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
