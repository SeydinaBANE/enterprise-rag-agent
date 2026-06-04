# BONNES-PRATIQUES.md

Règles non négociables pour contribuer à ce projet.

---

## Architecture

- Les dépendances ne vont que vers l'intérieur : `API → Agent → core/ ← infra/`
- `src/core/` ne doit jamais importer de bibliothèque externe (zéro dépendance)
- Le code ne dépend que des interfaces (`ILLMClient`, `IVectorStore`, `IDocumentLoader`, `ISessionStore`) — jamais des implémentations concrètes
- La configuration vient toujours de `settings` (pydantic-settings) — jamais de `os.environ` directement
- Les appels base de données et LLM restent dans `infra/` — jamais dans les routes API

## Exceptions

- Les exceptions métier (`GuardrailViolation`, `LLMError`, etc.) sont levées dans `domain/infra` et rattrapées dans les routes API
- Chaque nouvelle exception domaine s'ajoute dans `src/core/exceptions.py`
- Ne jamais laisser une `Exception` générique traverser une route — toujours convertir en `HTTPException`
- Mapping HTTP obligatoire : `EmbeddingError` → 502, `VectorStoreError` → 500, `LLMError` → 500, `GuardrailViolation` → 422, `UnsupportedSourceError` → 422
- Le handler global (`@app.exception_handler(Exception)` dans `main.py`) attrape tout le reste et retourne un JSON structuré avec `request_id` — ne pas dupliquer cette logique dans les routes

## Typage

- Tous les paramètres et valeurs de retour sont annotés
- Pas de `Any`, `dict`, `list` non typés — utiliser des types concrets
- Pas de `# type: ignore` sans commentaire expliquant pourquoi (voir `vector_store.py` pour l'exemple)
- `mypy --strict` doit passer sans erreur

## Tests

- Un test nominal + un test d'erreur/edge case minimum par fonction modifiée
- Mocker à la frontière des interfaces : `MockLLMClient`, `MockVectorStore`, `MockSessionStore` (voir `tests/conftest.py`)
- `side_effect` sur `mock_llm.complete` quand le test appelle `complete()` plusieurs fois (route + generate)
- Les tests d'intégration marqués `@pytest.mark.integration` et lancés séparément via `make test-integration`
- Ne jamais mocker `settings` directement — utiliser `monkeypatch.setattr(_cfg.settings, "api_key", ...)`

## Observabilité

- Toute nouvelle métrique Prometheus se déclare dans `src/observability/telemetry.py` comme singleton module-level
- Ne jamais instancier `Counter`, `Histogram` ou `Gauge` hors de `telemetry.py`
- Les histogrammes se mesurent avec `time.monotonic()` autour de l'appel à chronomètrer
- Les logs utilisent `structlog` — jamais `print()` ou `logging` directement

## Sécurité

- Toute entrée utilisateur passe par `filters.check_input()` avant d'atteindre l'agent
- Toute sortie LLM passe par `filters.check_output()` avant d'être retournée
- `X-API-Key` est obligatoire sur tous les endpoints data — jamais sur `/health` ni `/metrics`
- Pas de secrets, d'IPs, ni de chemins absolus dans le code
- Rate limiting via `@limiter.limit(settings.rate_limit_chat)` sur toute route coûteuse (LLM, ingest). Le paramètre `request: Request` doit être **en premier** dans la signature de la fonction pour que slowapi le détecte
- `ALLOWED_ORIGINS` doit être restreint en production — ne jamais laisser `["*"]` face à Internet

## Workflow Git

- Format des commits : `<type>(<scope>): <description>` — enforced par commitlint
- Types valides : `feat`, `fix`, `chore`, `docs`, `test`, `ci`, `refactor`, `perf`, `revert`
- `make check` doit passer entièrement avant tout commit (lint + typecheck + security + tests à 80%)
- Ne jamais committer `.env` ni aucun fichier contenant des clés

## Docker

- En dev : `make docker-up` pour les services tiers, `make run` pour l'app (hot reload)
- Pour rebuild l'image Compose : `docker compose up -d --build app` (pas `make docker-build` qui produit une image séparée)
- La collection ChromaDB est créée au premier ingest — si la dimension des embeddings change, supprimer la collection via l'API Chroma avant de réingérer
