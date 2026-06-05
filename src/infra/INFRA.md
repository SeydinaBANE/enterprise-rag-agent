# src/infra/

Adaptateurs d'infrastructure : implémentations concrètes des interfaces définies dans `src/core/ports.py`. Chaque classe de ce dossier dépend d'une librairie externe (ChromaDB, LiteLLM, psycopg) et traduit ses appels en contrats domain.

---

## Règle fondamentale

`src/infra/` peut importer `src/core/`. `src/core/` ne peut jamais importer `src/infra/`. Les classes concrètes ne sont instanciées que dans `create_app()` (`src/api/main.py`).

---

## `llm_client.py` — `LiteLLMClient`

Implémente `ILLMClient`. Toutes les requêtes passent par OpenRouter (`https://openrouter.ai/api/v1`) via la librairie `litellm`.

### Préfixe de modèle

Le préfixe `openrouter/` est ajouté **automatiquement** dans `complete()` et `embed()` :
```python
model=f"openrouter/{model or settings.llm_model}"
```
Les call sites passent le nom nu du modèle (ex. `"openai/gpt-4o-mini"`) — ne pas ajouter le préfixe manuellement.

### Retry avec backoff exponentiel — `_call_with_retry()`

```
Tentative 0  → échec → attente 0.5s
Tentative 1  → échec → attente 1.0s
Tentative 2  → échec → lève l'exception originale
```

Nombre de tentatives : `settings.llm_max_retries` (défaut 2). Timeout par appel : `settings.llm_timeout` secondes (défaut 60).

Toute exception de `complete()` est convertie en `LLMError`. Toute exception de `embed()` est convertie en `EmbeddingError`.

### `is_healthy()`

Fait un HEAD sur `https://openrouter.ai/api/v1/auth/key` avec la clé API. N'utilise pas `acompletion("ping")` pour éviter un appel payant au healthcheck.

---

## `vector_store.py` — `ChromaVectorStore`

Implémente `IVectorStore`. Client ChromaDB HTTP asynchrone.

### Initialisation lazy — `_get_client()`

`chromadb.AsyncHttpClient()` est une **coroutine factory**, pas un constructeur. Elle doit être `await`ée. Le client est créé une seule fois à la première utilisation et mis en cache dans `self._client`.

```python
client = await self._get_client()   # ✅ lazy, cached
client = chromadb.AsyncHttpClient() # ❌ ne pas faire sans await
```

### Collection unique — `COLLECTION_NAME = "documents"`

Toutes les ingestions vont dans la même collection ChromaDB. La collection est créée automatiquement au premier `add_chunks` via `get_or_create_collection`.

### Dimension d'embedding — `_check_dimension()`

La collection fixe sa dimension au premier `add_chunks`. Si la dimension change (changement de modèle d'embedding, ou conflit entre les 384-dim des tests et les 1536-dim de production), `_check_dimension()` lève une `VectorStoreError` avec un message explicatif.

**Pour réinitialiser :**
```bash
curl -X DELETE http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections/documents
```

### `add_chunks()`

Les embeddings sont passés à ChromaDB comme `list[list[float]]`. Les stubs ChromaDB attendent des tableaux numpy, d'où le `# type: ignore[arg-type]` — correct à l'exécution.

### `search()`

Retourne des `Chunk` avec de nouveaux UUIDs (les IDs de ChromaDB ne sont pas réexposés). Le score de distance n'est pas propagé dans `Chunk.embedding` — il est perdu à ce stade.

### `list_documents()`

Récupère tous les métadonnées, regroupe par `document_id`, compte les chunks par document. Retourne `list[tuple[str, int, str]]` : `(document_id, chunk_count, ingested_at_iso)`.

---

## `postgres_session_store.py` — `PostgresSessionStore`

Implémente `ISessionStore`. Utilisé quand `settings.postgres_dsn` est défini. Pool de connexions `psycopg_pool.AsyncConnectionPool`.

### Schéma SQL (auto-créé au démarrage)

```sql
CREATE TABLE IF NOT EXISTS rag_sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rag_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES rag_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rag_messages_session_idx
    ON rag_messages (session_id, created_at);
```

Le schéma est créé dans `_get_pool()` à la première connexion. Pas de migration versionnée (Alembic) pour l'instant — les changements de schéma nécessitent une intervention manuelle.

### `_get_pool()` — Initialisation lazy

Le pool est ouvert à la première utilisation, pas au constructeur. Taille configurée par `settings.postgres_pool_min` / `settings.postgres_pool_max`.

### `get_history()`

Récupère les `max_turns * 2` messages les plus récents (`ORDER BY created_at DESC LIMIT N`), puis les réordonne chronologiquement (`reversed()`).

### `add_message()`

Upsert de la session (`ON CONFLICT DO NOTHING`) puis insert du message. Pas de transaction explicite — les deux `execute` sont dans la même connexion de pool (auto-commit psycopg).

### `close()`

Ferme le pool de connexions. Appelé par le lifespan FastAPI à l'arrêt du serveur.

Toutes les exceptions Postgres sont wrappées en `VectorStoreError` (réutilisation pragmatique de l'exception infra générique).

---

## Ajouter un nouvel adaptateur

1. Créer `src/infra/<nom>.py`
2. Importer l'interface cible depuis `src/core/ports.py`
3. Implémenter toutes les méthodes abstraites
4. Wraper les exceptions externes en exceptions domaine (`src/core/exceptions.py`)
5. Injecter dans `create_app()` à la place ou en complément de l'adaptateur existant
6. Écrire au minimum un test unitaire (mock des appels externes) et un test d'intégration marqué `@pytest.mark.integration`
