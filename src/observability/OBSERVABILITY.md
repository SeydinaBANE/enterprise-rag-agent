# src/observability/

Module de métriques Prometheus. Déclare les métriques comme singletons au niveau module — importées directement dans les routes et l'agent.

---

## `telemetry.py`

Toutes les métriques sont des instances module-level de `prometheus_client`. **Ne pas créer de nouvelles instances dans les routes ou l'agent** — les déclarer ici et les importer.

```python
# Correct
from src.observability.telemetry import chat_requests_total
chat_requests_total.labels(status="ok").inc()

# Incorrect — crée un conflit de registre Prometheus
counter = Counter("chat_requests_total", ...)
```

---

## Métriques disponibles

### `chat_requests_total` — Counter

Total des requêtes `/chat`. Label `status` :

| Valeur | Condition |
|---|---|
| `"ok"` | Réponse retournée avec succès |
| `"blocked"` | Guardrail d'entrée déclenché (injection, longueur) |
| `"error"` | `LLMError` levée par l'agent |

### `ingest_requests_total` — Counter

Total des requêtes d'ingestion (`/documents/ingest` et `/documents/ingest/url`). Label `status` :

| Valeur | Condition |
|---|---|
| `"ok"` | Chunks stockés avec succès |
| `"unsupported"` | Format de fichier ou domaine non supporté |
| `"error"` | Erreur d'embedding ou de stockage |

### `retrieval_latency_seconds` — Histogram

Temps de la phase RAG (embed query + search ChromaDB). Observé dans `AgentGraph._rag_search()`.

Buckets : `[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]` secondes.

### `llm_latency_seconds` — Histogram

Temps de la phase de génération LLM. Observé dans `AgentGraph.invoke()` après `_generate()`.

Buckets : `[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]` secondes.

### `active_sessions` — Gauge

Nombre de sessions distinctes dans le store (in-memory ou Postgres). Mis à jour après chaque invocation de l'agent via `ISessionStore.count()`.

### `http_request_duration_seconds` — Histogram

Durée totale de chaque requête HTTP. Labels : `method`, `path`, `status`. Observé dans `RequestLoggingMiddleware`.

Buckets : `[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]` secondes.

---

## Endpoint Prometheus

`GET /metrics` dans `src/adapters/primary/api/routes/health.py` retourne `generate_latest()` avec le content-type `CONTENT_TYPE_LATEST`. Pas d'auth requise — prévu pour le scraping Prometheus interne.

---

## Dashboards Grafana

Le dashboard JSON est provisionné automatiquement depuis `docker/grafana/dashboard.json`. Voir `GRAFANA.md` pour les panels disponibles et les requêtes PromQL.

---

## Ajouter une métrique

1. Déclarer dans `telemetry.py` :
```python
my_new_counter = Counter("my_new_counter", "Description", ["label_a"])
```

2. Importer et utiliser dans la route ou le service concerné :
```python
from src.observability.telemetry import my_new_counter
my_new_counter.labels(label_a="value").inc()
```

3. Ajouter le panel correspondant dans `docker/grafana/dashboard.json` si nécessaire.
