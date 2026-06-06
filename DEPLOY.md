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

## Fly.io + Supabase + Vercel (gratuit)

### Architecture

```
Vercel (frontend, Next.js) — gratuit
  └─► Fly.io Web Service — rag-api (FastAPI, CHROMA_MODE=embedded)
          ├─► Fly Volume 3 GB — /data/chroma (ChromaDB embarqué)
          └─► Supabase PostgreSQL — sessions (gratuit)
```

ChromaDB tourne **en mode embarqué** (in-process) : plus de service séparé, les données sont persistées sur un volume Fly.

### Coûts

| Service | Plan | $/mois |
|---------|------|--------|
| Fly.io (shared-cpu-1x 512 MB) | Pay-as-you-go | ~$2–3 (auto-stop) |
| Fly Volume 3 GB | Inclus free tier | $0 |
| Supabase PostgreSQL | Free | $0 |
| Vercel (frontend) | Hobby | $0 |
| **Total** | | **~$2–3** |

> Avec `auto_stop_machines = 'stop'` dans `fly.toml`, la VM s'arrête si inactif — coût quasi nul en dehors des requêtes.

### Prérequis

```bash
# Installer flyctl
curl -L https://fly.io/install.sh | sh
fly auth login
```

### First deploy — Supabase

1. Créer un projet sur [supabase.com](https://supabase.com) (Free tier).
2. Récupérer la **Connection string** (mode Transaction, port 5432) dans Settings → Database.
3. La noter — elle sera passée comme secret Fly : `postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres`.

### First deploy — Fly.io

```bash
# 1. Créer l'app (ne pas déployer encore)
fly launch --no-deploy --name enterprise-rag-agent

# 2. Créer le volume persistant pour ChromaDB
fly volumes create chroma_data --region cdg --size 3

# 3. Injecter les secrets (jamais dans fly.toml)
fly secrets set \
  OPENROUTER_API_KEY=sk-... \
  API_KEY=votre-secret \
  POSTGRES_DSN="postgresql://postgres:...@db....supabase.co:5432/postgres" \
  ALLOWED_ORIGINS='["https://votre-app.vercel.app"]'

# 4. Déployer
fly deploy
```

### First deploy — Vercel

Identique à la section Render + Vercel ci-dessous, en remplaçant `NEXT_PUBLIC_API_URL` par l'URL Fly : `https://enterprise-rag-agent.fly.dev`.

### Redéploiement

```bash
fly deploy          # rebuild + redeploy
fly logs            # logs en temps réel
fly status          # état des machines
```

### Troubleshooting

**OOM / machine killed** — passer à 1 GB : modifier `memory = '1gb'` dans `fly.toml` (~$3.50/mois).

**Volume déjà monté** — si `fly volumes create` échoue car la machine est déjà créée : `fly volumes list` pour vérifier.

**Cold start lent** — normal avec `auto_stop = 'stop'` ; la première requête après inactivité réveille la VM (~3–5 s).

---

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
