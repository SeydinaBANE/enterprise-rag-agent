# GRAFANA.md

Dashboards de supervision de l'Enterprise RAG Agent.

---

## Accès

- URL : http://localhost:3000
- Identifiants par défaut : `admin` / `admin`
- Dashboard principal : http://localhost:3000/d/rag-agent-v1

---

## Dashboard « Enterprise RAG Agent »

Fichier source : `docker/grafana/dashboard.json` (UID `rag-agent-v1`)

| Panneau | Type | Métrique |
|---|---|---|
| Chat Requests (total) | Stat | `sum(chat_requests_total)` |
| Error Rate | Stat | ratio `error` / total sur 5 min |
| Active Sessions | Stat | `active_sessions` |
| LLM Latency P95 | Time series | `histogram_quantile(0.95, ...)` LLM + Retrieval |
| Request Rate | Time series | taux OK vs Error sur 5 min |

---

## Provisioning automatique

Au démarrage du container Grafana, deux fichiers sont chargés automatiquement :

```
docker/grafana/provisioning/
├── datasources/prometheus.yml   → datasource Prometheus sur http://prometheus:9090
└── dashboards/provider.yml      → pointe vers /etc/grafana/dashboards/
docker/grafana/dashboard.json    → monté dans /etc/grafana/dashboards/
```

Aucune configuration manuelle n'est requise après `make docker-up`.

---

## Modifier le dashboard

1. Éditer le dashboard dans l'UI Grafana
2. Exporter via **Share → Export → Save to file**
3. Remplacer `docker/grafana/dashboard.json` par le fichier exporté
4. Relancer le container : `docker compose up -d --force-recreate grafana`

> Ne pas modifier `dashboard.json` manuellement — Grafana génère des champs internes (`id`, `iteration`) qui peuvent casser le provisioning.

---

## Ajouter un dashboard

1. Créer le fichier JSON dans `docker/grafana/`
2. Ajouter un volume dans `docker-compose.yml` :
   ```yaml
   - ./docker/grafana/mon-dashboard.json:/etc/grafana/dashboards/mon-dashboard.json:ro
   ```
3. Relancer Grafana — `provider.yml` scanne tout le dossier `/etc/grafana/dashboards/`
