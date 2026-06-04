# PROMETHEUS.md

Monitoring de l'Enterprise RAG Agent via Prometheus.

---

## Accès

- UI Prometheus : http://localhost:9090
- Endpoint métriques API : http://localhost:8000/metrics

---

## Métriques exposées

### Counters

| Métrique | Labels | Description |
|---|---|---|
| `chat_requests_total` | `status` (`ok`, `error`, `blocked`) | Requêtes chat cumulées |
| `ingest_requests_total` | `status` (`ok`, `error`, `unsupported`) | Requêtes d'ingestion cumulées |

### Histogrammes

| Métrique | Buckets (s) | Description |
|---|---|---|
| `llm_latency_seconds` | 0.1, 0.5, 1, 2, 5, 10, 30 | Durée de la génération LLM (`_generate`) |
| `retrieval_latency_seconds` | 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5 | Durée de la recherche RAG (`_rag_search`) |

### Gauge

| Métrique | Description |
|---|---|
| `active_sessions` | Nombre de sessions actives (mis à jour après chaque requête) |

---

## Requêtes utiles

```promql
# Taux de requêtes OK par seconde (fenêtre 5 min)
sum(rate(chat_requests_total{status="ok"}[5m]))

# Taux d'erreurs LLM
sum(rate(chat_requests_total{status="error"}[5m]))

# Taux de blocage guardrail
sum(rate(chat_requests_total{status="blocked"}[5m]))

# Latence LLM P95
histogram_quantile(0.95, rate(llm_latency_seconds_bucket[5m]))

# Latence LLM P50 (médiane)
histogram_quantile(0.50, rate(llm_latency_seconds_bucket[5m]))

# Latence retrieval P95
histogram_quantile(0.95, rate(retrieval_latency_seconds_bucket[5m]))

# Latence LLM moyenne
rate(llm_latency_seconds_sum[5m]) / rate(llm_latency_seconds_count[5m])
```

---

## Configuration du scrape

Fichier : `prometheus.yml`

```yaml
scrape_configs:
  - job_name: "enterprise-rag-agent"
    static_configs:
      - targets: ["app:8000"]   # nom Docker Compose
    metrics_path: /metrics
    scrape_interval: 15s
```

En dev local (`make run`), remplacer `app:8000` par `host.docker.internal:8000`.

---

## Ajouter une nouvelle métrique

1. Déclarer le singleton dans `src/observability/telemetry.py` (Counter, Histogram, ou Gauge)
2. L'importer et l'appeler à l'endroit voulu dans le code
3. Ne jamais instancier deux fois le même nom — Prometheus lève une erreur au démarrage
