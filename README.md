<div align="center">

# Enterprise RAG Agent

**Production-grade agentic RAG system for enterprise knowledge management**

[![CI](https://github.com/SeydinaBANE/enterprise-rag-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/SeydinaBANE/enterprise-rag-agent/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white)](https://nextjs.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-1C3C3C?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
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
  LangGraph Agent ──→ OpenRouter LLM ──→ Réponse citée
        ↓ retrieval
   ChromaDB (vecteurs) ← Documents (PDF, TXT, URL)
```

---

## Fonctionnalités

| Fonctionnalité | Détail |
|---|---|
| **Interface web** | Next.js 16 — chat, gestion documents, paramètres, health status en temps réel |
| **Agent autonome** | LangGraph — route automatiquement entre RAG et réponse directe |
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

# 3. Démarrer les services (ChromaDB, Postgres, Prometheus, Grafana)
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
├── api/            # FastAPI routes, lifespan, global exception handler
│   ├── routes/     # chat (rate-limited), documents, health + metrics
│   └── middleware/ # API key auth, rate limiter (slowapi), request logging
├── agent/          # LangGraph AgentGraph — route → rag_search → generate
├── core/           # Domain pur — ports (ABCs), models, exceptions, config
├── infra/          # Adaptateurs — LiteLLMClient, ChromaVectorStore, PostgresSessionStore
├── rag/            # Pipeline d'ingestion — loader, splitter, embedder, retriever
├── guardrails/     # Filtres input/output — injection, PII
└── observability/  # Métriques Prometheus — singletons module-level
```

**Règle d'or** : les dépendances ne vont que vers `core/`. `infra/` et `api/` implémentent les interfaces de `core/` — jamais l'inverse.

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
make check          # lint + typecheck + sécurité + tests (tout doit passer)
make test           # tests unitaires seuls — rapide, sans Docker
make test-integration  # tests e2e — nécessite make docker-up
```

- **80 %** de couverture requise sur les tests unitaires
- Lint : `ruff`, Typage : `mypy --strict`, Sécurité : `bandit`
- Pre-commit hooks : ruff, mypy, detect-private-key, commitlint

---

## Variables d'environnement

| Variable | Obligatoire | Défaut | Description |
|---|---|---|---|
| `OPENROUTER_API_KEY` | ✅ | — | Clé OpenRouter |
| `API_KEY` | ✅ | — | Token `X-API-Key` pour les clients |
| `LLM_MODEL` | | `openai/gpt-4o-mini` | Modèle de chat |
| `EMBEDDING_MODEL` | | `openai/text-embedding-3-small` | Modèle d'embedding |
| `CHROMA_HOST` | | `localhost` | Hôte ChromaDB |
| `CHROMA_PORT` | | `8001` | Port ChromaDB |
| `LLM_TIMEOUT` | | `60` | Timeout appel LLM (secondes) |
| `LLM_MAX_RETRIES` | | `2` | Tentatives max LLM avec backoff exponentiel |
| `MAX_UPLOAD_SIZE_MB` | | `50` | Taille max upload (Mo) |
| `ALLOWED_ORIGINS` | | `["http://localhost:3000"]` | Origines CORS autorisées — restreindre en prod |
| `RATE_LIMIT_CHAT` | | `20/minute` | Rate limit `/chat` par IP |
| `RATE_LIMIT_INGEST` | | `5/minute` | Rate limit `/documents/ingest*` par IP |
| `POSTGRES_DSN` | | _(in-memory)_ | DSN Postgres pour sessions persistantes |
| `POSTGRES_POOL_MIN` | | `2` | Connexions min pool Postgres |
| `POSTGRES_POOL_MAX` | | `10` | Connexions max pool Postgres |
| `ALLOWED_URL_DOMAINS` | | `[]` | Domaines autorisés pour ingestion URL (vide = tous) |
| `TRUSTED_PROXIES` | | `0` | Nombre de reverse proxies de confiance |
| `WORKERS` | | `1` | Workers uvicorn — mettre `4` en prod |
| `MAX_CHUNK_SIZE` | | `512` | Taille max des chunks (tokens) |
| `RETRIEVAL_TOP_K` | | `5` | Nombre de chunks retournés par requête |

---

## Documentation

| Fichier | Contenu |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Guide architecture pour Claude Code |
| [RUN.md](RUN.md) | Runbook opérationnel complet |
| [frontend/README.md](frontend/README.md) | Guide démarrage interface web |
| [BONNES-PRATIQUES.md](BONNES-PRATIQUES.md) | Règles de contribution |
| [PROMETHEUS.md](PROMETHEUS.md) | Métriques et requêtes PromQL |
| [GRAFANA.md](GRAFANA.md) | Dashboards et provisioning |
| [BUILD.md](BUILD.md) | Build et gestion des dépendances |
| [DEPLOY.md](DEPLOY.md) | Déploiement et opérations |
| [docs/architecture.md](docs/architecture.md) | Diagrammes d'architecture |
| [docs/adr/](docs/adr/) | Architecture Decision Records |

---

## Licence

MIT — voir [LICENSE](LICENSE).
