# src/adapters/primary/api/

Couche de présentation HTTP : expose les endpoints FastAPI, applique l'authentification, le rate limiting, le logging, et convertit les exceptions domaine en réponses HTTP.

---

## Rôle dans l'architecture

```
HTTP Client
    ↓
middleware/auth.py       → vérifie X-API-Key
middleware/logging.py    → log structuré + métriques HTTP
middleware/ratelimit.py  → limite le débit par IP
    ↓
routes/chat.py           → POST /chat
routes/documents.py      → POST /documents/ingest, GET /documents
routes/health.py         → GET /health, GET /metrics
    ↓
app.state.*              → services injectés au démarrage (agent, pipeline, vector_store…)
```

---

## `main.py` — Composition root

Point d'entrée unique. Responsable de :

1. **Construire tous les services** et les stocker sur `app.state`
2. **Enregistrer les middlewares** dans l'ordre correct
3. **Configurer l'app FastAPI** (docs, CORS, lifespan)

### `create_app()` → `FastAPI`

Instancie dans l'ordre :

```python
llm_client   = LiteLLMClient()
vector_store = ChromaVectorStore()
embedder     = Embedder(llm_client)
retriever    = Retriever(vector_store, embedder)
session_store = _build_session_store()     # InMemory ou Postgres
rag_tool     = RAGSearchTool(vector_store, embedder)
pipeline     = IngestPipeline(vector_store, embedder)
agent        = build_agent(llm_client, rag_tool, session_store)
```

Tous ces objets sont stockés sur `app.state` et accédés dans les routes via `request.app.state.<service>`.

**Ne jamais instancier ces services dans les routes** — toujours les lire depuis `app.state`.

### `_lifespan(app)`

Vérifie ChromaDB et Postgres au démarrage avant d'accepter le premier request (fail-fast). Ferme proprement le pool Postgres à l'arrêt.

### Swagger / OpenAPI

Désactivés si `settings.app_env == "production"` (`docs_url=None`, `redoc_url=None`, `openapi_url=None`). En développement, Swagger est accessible sur `/docs`.

### CORS

```python
allow_origins  = settings.allowed_origins  # ex. ["https://rag.example.com"]
allow_methods  = ["GET", "POST"]
allow_headers  = ["Content-Type", "X-API-Key"]
allow_credentials = False
```

### Handler d'exceptions global

Toute exception non interceptée retourne `{"detail": "Internal server error", "request_id": "<uuid>"}` (HTTP 500 JSON). Le traceback complet est loggé côté serveur, jamais exposé au client.

---

## `middleware/`

### `auth.py` — Authentification API Key

Dépendance FastAPI (`Depends`) injectée sur chaque route protégée.

```python
async def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    if api_key is None or not hmac.compare_digest(api_key, settings.api_key):
        raise HTTPException(status_code=401, ...)
```

`hmac.compare_digest` protège contre les timing attacks (comparaison en temps constant).

Les endpoints `/health` et `/metrics` n'ont **pas** cette dépendance — intentionnel pour le scraping Prometheus et les health checks load balancer.

### `logging.py` — Middleware de logging HTTP

`RequestLoggingMiddleware` (Starlette `BaseHTTPMiddleware`) :

- Génère un `request_id` UUID par requête → stocké sur `request.state.request_id`
- Log structuré JSON (`structlog`) après la réponse : méthode, path, status code, durée ms
- Observe `http_request_duration_seconds` (Histogram Prometheus, labels : method, path, status)

Le `request_id` est repris par le handler d'exceptions global pour la corrélation des logs.

### `ratelimit.py` — Rate limiting par IP

`Limiter` slowapi avec résolution IP proxy-aware :

```
trusted_proxies = 0  →  utilise request.client.host (IP directe)
trusted_proxies = N  →  prend le N-ième IP depuis la droite dans X-Forwarded-For
```

Appliqué avec `@limiter.limit(settings.rate_limit_chat)` sur la route. **La signature de la route doit avoir `request: Request` en premier paramètre** pour que slowapi puisse accéder à l'IP.

Configurer `TRUSTED_PROXIES=1` quand l'app est derrière un reverse proxy (Nginx/Caddy).

---

## `routes/`

### `chat.py` — POST /chat

Flux :
1. `check_input(body.message)` → `GuardrailViolation` → 422
2. `agent.invoke(message, session_id)` → `LLMError` → 500
3. `check_output(response.answer)` → rédaction PII
4. Incrémente `chat_requests_total` (label : `ok` | `blocked` | `error`)

`body.session_id` est `"default"` si non fourni. Pas de validation de format — voir les contraintes de `ChatRequest` dans `src/domain/models.py`.

### `documents.py` — Ingestion et listing

#### `POST /documents/ingest` (multipart file)

1. Lit le fichier en mémoire, rejette si > `MAX_UPLOAD_SIZE_MB` (→ 413)
2. Écrit dans un fichier temporaire avec le bon suffixe
3. Lance `pipeline.run(tmp_path)`
4. Supprime le fichier temporaire dans le `finally` (via `Path.unlink(missing_ok=True)`)

Exceptions :
- `UnsupportedSourceError` → 422 (format non supporté)
- `EmbeddingError` → 502 (service d'embedding indisponible)
- `VectorStoreError` → 500 (ChromaDB inaccessible)

#### `POST /documents/ingest/url` (JSON)

Même pipeline, la validation SSRF est effectuée dans `URLLoader._validate_url()`.

#### `GET /documents`

Appelle `vector_store.list_documents()` → liste `(document_id, chunk_count, ingested_at_iso)`. Retourne `{"documents": [...], "total": N}`.

### `health.py` — GET /health et GET /metrics

#### `GET /health`

Vérifie ChromaDB, LLM (HEAD sur OpenRouter), et session store. Retourne :
```json
{"status": "ok"|"degraded", "chromadb": "ok"|"error", "llm": "ok"|"error",
 "sessions": "ok"|"error", "uptime_seconds": 123}
```

Utilisé par le Docker healthcheck et les load balancers. Pas d'auth requise.

#### `GET /metrics`

Retourne le texte Prometheus (`generate_latest()`). Pas d'auth requise — à protéger par réseau en production (ne pas exposer le port 8000 publiquement).

---

## Tableau des endpoints

| Méthode | Path | Auth | Rate limit | Notes |
|---|---|---|---|---|
| POST | `/chat` | X-API-Key | 20/min | Guardrails input + output |
| POST | `/documents/ingest` | X-API-Key | 5/min | Multipart, max 50 MB |
| POST | `/documents/ingest/url` | X-API-Key | 5/min | JSON `{"url": "..."}` |
| GET | `/documents` | X-API-Key | — | |
| GET | `/health` | aucune | — | Utilisé par Docker healthcheck |
| GET | `/metrics` | aucune | — | Scraping Prometheus |

---

## Ajouter une route

1. Créer `src/adapters/primary/api/routes/<nom>.py` avec un `router = APIRouter()`
2. Ajouter `Depends(require_api_key)` si la route nécessite une auth
3. Inclure le router dans `create_app()` : `app.include_router(<nom>.router)`
4. Incrémenter un counter Prometheus dans chaque branche de la route
