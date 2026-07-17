<div align="center">

# Enterprise RAG Agent

**Production-grade agentic RAG system for enterprise knowledge management**

[![CI](https://github.com/SeydinaBANE/enterprise-rag-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/SeydinaBANE/enterprise-rag-agent/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white)](https://nextjs.org/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5+-FF6719?logoColor=white)](https://www.trychroma.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![codecov](https://codecov.io/gh/SeydinaBANE/enterprise-rag-agent/branch/main/graph/badge.svg)](https://codecov.io/gh/SeydinaBANE/enterprise-rag-agent)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230?logo=ruff)](https://github.com/astral-sh/ruff)

</div>

---

## Vue d'ensemble

Un agent RAG (Retrieval-Augmented Generation) autonome, prêt pour la production. L'agent décide seul s'il doit chercher dans la base documentaire ou répondre directement, cite ses sources, et maintient un historique de conversation par session.

```
  Next.js UI (localhost:3000)
        ↓ REST (X-API-Key)
   FastAPI REST API (localhost:8000)
        ↓
  AgentGraph ──→ OpenRouter LLM ──→ Réponse citée
        ↓ retrieval
   ChromaDB (vecteurs) ← Documents (PDF, TXT, URL)
```

---

## Fonctionnalités

| Fonctionnalité | Détail |
|---|---|
| **Interface web** | Next.js 16 — chat, gestion documents, paramètres, health status en temps réel |
| **Agent autonome** | AgentGraph — route automatiquement entre RAG et réponse directe |
| **Ingestion multi-format** | PDF, TXT, MD, RST, URLs web (BeautifulSoup) |
| **Protection SSRF** | Résolution DNS + blocage IPs privées sur toute ingestion URL |
| **Limite d'upload** | 50 Mo max par fichier (configurable) |
| **Mémoire de session** | Historique par `session_id`, max 10 tours (in-memory ou Postgres avec pool configurable) |
| **Guardrails** | Détection d'injection de prompt, redaction PII (SSN, email, téléphone) |
| **Rate limiting** | slowapi — `/chat` 20 req/min, `/ingest` 5 req/min par IP (proxy-aware) |
| **Startup health check** | Vérifie ChromaDB et Postgres au démarrage — fail-fast avant d'accepter du trafic |
| **Graceful shutdown** | Ferme le pool Postgres proprement à l'arrêt (SIGTERM) |
| **Observabilité** | Prometheus metrics (latence LLM/retrieval, requêtes, sessions) + Grafana |
| **Clean Architecture** | 4 couches strictes, dépendances uniquement vers l'intérieur |
| **CI/CD** | GitHub Actions — lint, typecheck, sécurité, couverture 80%, Trivy, tests e2e |

---

## Démarrage rapide

### Prérequis

- Python 3.12+ avec [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- Docker & Docker Compose
- Clé API [OpenRouter](https://openrouter.ai)

### Installation

```bash
# 1. Cloner et installer
git clone https://github.com/SeydinaBANE/enterprise-rag-agent.git
cd enterprise-rag-agent
make install

# 2. Configurer l'environnement
cp .env.example .env
# Renseigner OPENROUTER_API_KEY et API_KEY dans .env

# 3. Démarrer les services (ChromaDB, Postgres, Prometheus, frontend:3000, Grafana:3001)
make docker-up

# 4. Lancer l'API en mode développement (hot reload)
docker compose stop app   # libérer le port 8000
make run
# → http://localhost:8000/docs

# 5. Lancer l'interface web (dans un autre terminal)
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
# → http://localhost:3000
```

---

## Utilisation

### Ingérer un document

```bash
# Fichier local (PDF, TXT, MD…)
curl -X POST http://localhost:8000/documents/ingest \
  -H "X-API-Key: your-api-key" \
  -F "file=@contrat.pdf"

# URL web
curl -X POST http://localhost:8000/documents/ingest/url \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

### Interroger l'agent

```bash
curl -X POST http://localhost:8000/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Que dit le contrat sur les conditions de résiliation ?",
    "session_id": "session-user-1"
  }'
```

```json
{
  "answer": "Selon [Source: contrat.pdf], la résiliation...",
  "sources": [{"document_id": "contrat.pdf", "chunk": "...", "score": 0.0}],
  "session_id": "session-user-1",
  "used_retrieval": true,
  "latency_ms": 1842.3
}
```

### Lister les documents ingérés

```bash
curl http://localhost:8000/documents \
  -H "X-API-Key: your-api-key"
```

---

## Architecture

```
src/
├── domain/                    # Domaine pur — models, exceptions, config (zéro dépendance framework)
├── ports/
│   ├── inbound.py             # Ports entrants (driving) — IChatUseCase, IIngestUseCase
│   └── outbound.py            # Ports sortants (driven) — ILLMClient, IVectorStore, ISessionStore, IDocumentLoader
├── application/                # Use cases — orchestration, découplée de FastAPI
│   ├── agent/                 # AgentGraph implémente IChatUseCase — route → rag_search → generate
│   └── rag/                   # IngestPipeline implémente IIngestUseCase — ingestion/ (splitter, pipeline), embedder, retriever
├── adapters/
│   ├── primary/api/           # Adaptateur pilotant — FastAPI routes, lifespan, global exception handler
│   │   ├── routes/            # chat (rate-limited), documents, health + metrics
│   │   └── middleware/        # API key auth, rate limiter (slowapi), request logging
│   └── secondary/              # Adaptateurs pilotés — LiteLLMClient, ChromaVectorStore, PostgresSessionStore, loaders (URL/PDF/Text)
├── guardrails/                 # Filtres input/output (cross-cutting) — injection, PII
└── observability/               # Métriques Prometheus (cross-cutting) — singletons module-level
```

**Règle d'or (hexagonale)** : les dépendances ne vont que vers `domain/` et `ports/`. `application/` implémente les ports entrants et dépend des ports sortants ; `adapters/secondary/` implémente les ports sortants ; `adapters/primary/` déclenche les ports entrants. Jamais l'inverse.

---

## Observabilité

| Service | URL | Accès |
|---|---|---|
| Interface web | http://localhost:3000 | clé API |
| API docs (Swagger) | http://localhost:8000/docs | public |
| Métriques Prometheus | http://localhost:8000/metrics | public |
| Prometheus UI | http://localhost:9090 | — |
| Grafana | http://localhost:3001 | admin / admin |

Le dashboard Grafana est provisionné automatiquement au démarrage avec :
- Nombre de requêtes chat (total + taux par statut)
- Sessions actives
- Latence LLM P95 et Retrieval P95

---

## Qualité & Tests

```bash
make check          # lint + format-check + typecheck + sécurité + tests (tout doit passer)
make test           # tests unitaires seuls — rapide, sans Docker
make test-integration  # tests e2e — nécessite make docker-up
```

- **80 %** de couverture requise sur les tests unitaires
- Lint : `ruff`, Typage : `mypy --strict`, Sécurité : `bandit`
- Pre-commit hooks : ruff, mypy, detect-private-key (commitlint non enforced — validation manuelle)

---

## Variables d'environnement

| Variable | Obligatoire | Défaut | Description |
|---|---|---|---|
| `OPENROUTER_API_KEY` | ✅ | — | Clé OpenRouter |
| `API_KEY` | ✅ | — | Token `X-API-Key` pour les clients |
| `LLM_MODEL` | | `openai/gpt-4o-mini` | Modèle de chat |
| `EMBEDDING_MODEL` | | `openai/text-embedding-3-small` | Modèle d'embedding |
| `CHROMA_MODE` | | `http` | Mode ChromaDB : `http` (service externe) ou `embedded` (in-process, Fly.io) |
| `CHROMA_DATA_PATH` | | `/data/chroma` | Répertoire de persistance — mode `embedded` uniquement |
| `CHROMA_HOST` | | `localhost` | Hôte ChromaDB — mode `http` uniquement |
| `CHROMA_PORT` | | `8001` | Port ChromaDB — mode `http` uniquement |
| `LLM_TIMEOUT` | | `60` | Timeout appel LLM (secondes) |
| `LLM_MAX_RETRIES` | | `2` | Tentatives max LLM avec backoff exponentiel |
| `MAX_UPLOAD_SIZE_MB` | | `50` | Taille max upload (Mo) |
| `ALLOWED_ORIGINS` | | `["http://localhost:3000"]` | Origines CORS autorisées — restreindre en prod |
| `RATE_LIMIT_CHAT` | | `20/minute` | Rate limit `/chat` par IP |
| `RATE_LIMIT_INGEST` | | `5/minute` | Rate limit `/documents/ingest*` par IP |
| `POSTGRES_DSN` | | _(in-memory)_ | DSN Postgres pour sessions persistantes |
| `POSTGRES_POOL_MIN` | | `2` | Connexions min pool Postgres |
| `POSTGRES_POOL_MAX` | | `10` | Connexions max pool Postgres |
| `ALLOWED_URL_DOMAINS` | | `""` | Domaines autorisés pour ingestion URL, séparés par virgule (vide = tous) |
| `TRUSTED_PROXIES` | | `0` | Nombre de reverse proxies de confiance |
| `WORKERS` | | `1` | Workers uvicorn — mettre `4` en prod |
| `MAX_CHUNK_SIZE` | | `512` | Taille max des chunks (tokens) |
| `RETRIEVAL_TOP_K` | | `5` | Nombre de chunks retournés par requête |

---

## Déploiement cloud

Deux configurations prêtes à l'emploi — voir [DEPLOY.md](DEPLOY.md) pour le guide complet.

| Stack | Coût / mois | Notes |
|---|---|---|
| **Fly.io** + Supabase + Vercel | ~$2–3 | ChromaDB embarqué (`CHROMA_MODE=embedded`), volume 3 GB, auto-stop |
| **Render** + Vercel | ~$16.50 | ChromaDB service privé dédié, stack Docker Compose |

```bash
# Fly.io — déploiement rapide
fly launch --no-deploy --name enterprise-rag-agent
fly volumes create chroma_data --region cdg --size 3
fly secrets set OPENROUTER_API_KEY=... API_KEY=... POSTGRES_DSN=... ALLOWED_ORIGINS='[...]'
fly deploy
```

---

## Documentation

| Fichier | Contenu |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Guide architecture pour Claude Code |
| [CLI.md](CLI.md) | Référence complète des endpoints REST et commandes make |
| [RUN.md](RUN.md) | Runbook opérationnel complet |
| [DEV.md](DEV.md) | Guide développeur — workflow, conventions, extensions |
| [frontend/README.md](frontend/README.md) | Guide démarrage interface web |
| [BUILD.md](BUILD.md) | Build, dépendances et quality gates |
| [DEPLOY.md](DEPLOY.md) | Déploiement et opérations |
| [PROMETHEUS.md](PROMETHEUS.md) | Métriques et requêtes PromQL |
| [GRAFANA.md](GRAFANA.md) | Dashboards et provisioning |
| [docs/architecture.md](docs/architecture.md) | Diagrammes d'architecture |
| [docs/adr/](docs/adr/) | Architecture Decision Records |

---

## Licence

MIT — voir [LICENSE](LICENSE).
