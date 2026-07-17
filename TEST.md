# TEST.md

Guide complet des tests du projet Enterprise RAG Agent.

---

## Lancer les tests

```bash
# Tests unitaires (rapides, aucun Docker requis)
make test
uv run pytest tests/unit/ -v

# Un seul fichier
uv run pytest tests/unit/test_guardrails.py -v

# Un seul test
uv run pytest tests/unit/test_agent_graph.py::test_agent_invoke_rag_path -v

# Avec filtre par nom
uv run pytest -k "injection" -v

# Tests d'intégration (ChromaDB requis)
make docker-up
make test-integration

# Tout (unit + integration)
make test-all

# Sans seuil de couverture (utile en dev)
uv run pytest tests/unit/ --no-cov -v
```

Les tests unitaires n'ont besoin d'aucune variable d'environnement réelle — `OPENROUTER_API_KEY=test API_KEY=test-api-key` sont suffisants. Le Makefile les injecte automatiquement.

---

## Architecture des tests

```
tests/
├── conftest.py            ← fixtures et mocks partagés (tous les tests)
├── unit/                  ← pas de Docker, pas de réseau, pas de LLM réel
│   ├── test_rag_pipeline.py
│   ├── test_agent_graph.py
│   ├── test_guardrails.py
│   └── test_api_routes.py
└── integration/
    └── test_e2e_chat.py   ← ChromaDB réel, LLM mocké
```

**Règle** : les tests unitaires ne doivent jamais instancier `ChromaVectorStore` ni `LiteLLMClient`. Toute dépendance externe passe par `MockLLMClient` ou `MockVectorStore`.

---

## Fixtures partagées (`tests/conftest.py`)

Trois fixtures disponibles dans tous les fichiers de test :

```python
mock_llm        # MockLLMClient — remplace ILLMClient
mock_vector_store  # MockVectorStore — remplace IVectorStore
sample_chunk    # Chunk prérempli pour les assertions
```

### `MockLLMClient`

```python
class MockLLMClient:
    complete: AsyncMock   # return_value = "Test answer"
    embed: AsyncMock      # return_value = [[0.1] * 384]
    is_healthy: AsyncMock # return_value = True
```

**Pourquoi pas une sous-classe de `ILLMClient`** : Python vérifie à l'instanciation que toutes les méthodes `@abstractmethod` sont définies au niveau classe. Assigner `self.complete = AsyncMock()` dans `__init__` ne satisfait pas cette vérification. Les mocks sont donc des classes indépendantes.

### `MockVectorStore`

```python
class MockVectorStore:
    add_chunks: AsyncMock      # ne retourne rien par défaut
    search: AsyncMock          # return_value = [] (liste vide)
    list_documents: AsyncMock  # return_value = [] (ou [(id, count, ingested_at)])
    is_healthy: AsyncMock      # return_value = True
```

---

## Patterns de mock courants

### Appels multiples à `complete`

L'agent appelle `complete` deux fois dans le chemin RAG : une fois pour le routing, une fois pour la génération. Utiliser `side_effect` avec une liste :

```python
mock_llm.complete.side_effect = ["RAG", "Voici la réponse basée sur les documents."]
# Premier appel → "RAG" (routing)
# Deuxième appel → "Voici la réponse..." (génération)
```

Si un seul appel est attendu, `return_value` suffit :

```python
mock_llm.complete.return_value = "DIRECT"
```

### Mock d'embed pour le pipeline

Le pipeline appelle `embed(texts)` avec autant de textes qu'il y a de chunks. Utiliser `side_effect` avec un lambda pour correspondre dynamiquement :

```python
mock_llm.embed.side_effect = lambda texts: [[0.1] * 384] * len(texts)
```

Ne pas utiliser `return_value = [[0.1] * 384] * N` avec N fixe — si le splitter produit un nombre différent de chunks, `zip(..., strict=True)` lève une `ValueError`.

### Mock de résultats de recherche

```python
mock_vector_store.search.return_value = [sample_chunk]
```

### Vérifier qu'un appel a bien eu lieu

```python
mock_vector_store.add_chunks.assert_called_once()
mock_llm.embed.assert_called_once_with(["hello", "world"])
mock_llm.embed.assert_not_called()
```

---

## Tests de routes API (`test_api_routes.py`)

Le client de test reconstruit l'app avec les mocks injectés sur `app.state` :

```python
@pytest.fixture
def client(mock_llm, mock_vector_store) -> TestClient:
    app = create_app()
    # Remplace les services instanciés par create_app()
    app.state.llm_client = mock_llm
    app.state.vector_store = mock_vector_store
    # ... reconstruire agent, pipeline, embedder avec les mocks ...
    return TestClient(app)
```

`API_KEY` dans les tests est `"test-api-key"` (valeur injectée via env var). Les routes protégées nécessitent `headers={"X-API-Key": "test-api-key"}`.

```python
# Route protégée — sans clé → 401
response = client.post("/chat", json={"message": "hello"})
assert response.status_code == 401

# Avec clé
response = client.post(
    "/chat",
    json={"message": "hello", "session_id": "test"},
    headers={"X-API-Key": "test-api-key"},
)
assert response.status_code == 200
```

### SSRF guard tests

The SSRF guard blocks private IPs. Test via URL ingestion with a private IP:

```python
def test_ingest_url_ssrf_private_ip(client: TestClient) -> None:
    response = client.post(
        "/documents/ingest/url",
        json={"url": "http://10.0.0.1/secret"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 422
    assert "private" in response.json()["detail"].lower()
```

### File upload limit tests

Uploading a file exceeding `MAX_UPLOAD_SIZE_MB` returns HTTP 413:

```python
def test_upload_exceeds_limit(client: TestClient) -> None:
    oversized_data = b"x" * (50 * 1024 * 1024 + 1)
    response = client.post(
        "/documents/ingest",
        files={"file": ("big.pdf", oversized_data, "application/pdf")},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 413
```

### Ingestion metadata tests

After ingesting a document, `list_documents` returns the `ingested_at` timestamp from ChromaDB metadata:

```python
async def test_ingested_at_in_metadata(
    mock_vector_store: MockVectorStore,
) -> None:
    mock_vector_store.list_documents.return_value = [
        ("doc-1", 3, "2026-06-04T12:00:00")
    ]
    result = await mock_vector_store.list_documents()
    assert len(result) == 1
    doc_id, chunk_count, ingested_at = result[0]
    assert isinstance(ingested_at, str)
    assert "T" in ingested_at
```

---

## Tests d'intégration (`test_e2e_chat.py`)

Nécessitent ChromaDB réel. Le LLM reste mocké (aucun appel OpenRouter en test).

```bash
make docker-up          # démarre ChromaDB sur le port 8001
make test-integration
make docker-down
```

La fixture est `scope="module"` : ChromaVectorStore est instancié une seule fois pour tout le fichier. Les imports des classes infra se font à l'intérieur du fixture, pas en tête de module — pour que l'import ne tente pas de se connecter à ChromaDB au chargement du fichier :

```python
@pytest.fixture(scope="module")
def integration_client() -> TestClient:
    from src.adapters.secondary.vector_store import ChromaVectorStore  # import local intentionnel
    vector_store = ChromaVectorStore()
    ...
```

En CI, ChromaDB est fourni comme service Docker dans `.github/workflows/ci.yml` :
```yaml
services:
  chromadb:
    image: chromadb/chroma:latest
    ports: ["8001:8000"]
```

---

## Couverture

Seuil minimum : **80%** (enforced par `--cov-fail-under=80` dans `pyproject.toml`).

```bash
# Rapport terminal
uv run pytest tests/unit/ --cov=src --cov-report=term-missing

# Rapport HTML
uv run pytest tests/unit/ --cov=src --cov-report=html
open htmlcov/index.html
```

`src/observability/` est exclu du seuil dans `codecov.yml` (code de télémétrie pur, pas de logique testable unitairement).

---

## Écrire un nouveau test

### Cas nominal + edge case (minimum requis)

```python
# Nominal
def test_splitter_short_document() -> None:
    doc = Document(id="d1", content="hello world", source="test.txt")
    splitter = TextSplitter(chunk_size=50, chunk_overlap=5)
    chunks = splitter.split(doc)
    assert len(chunks) == 1
    assert chunks[0].content == "hello world"

# Edge case
def test_splitter_empty_document() -> None:
    doc = Document(id="d1", content="   ", source="test.txt")
    splitter = TextSplitter(chunk_size=10, chunk_overlap=2)
    chunks = splitter.split(doc)
    assert chunks == []
```

### Test d'exception

```python
def test_check_input_too_long() -> None:
    with pytest.raises(GuardrailViolation, match="exceeds"):
        check_input("x" * 5000)
```

Toujours passer `match=` pour vérifier que c'est la bonne raison d'échec, pas n'importe quelle `GuardrailViolation`.

### Test async

```python
async def test_embedder_empty_input(mock_llm: MockLLMClient) -> None:
    embedder = Embedder(mock_llm)
    result = await embedder.embed([])
    assert result == []
    mock_llm.embed.assert_not_called()
```

`asyncio_mode = "auto"` est activé dans `pyproject.toml` — ne **pas** ajouter `@pytest.mark.asyncio` sur les tests async, cela provoque une erreur `duplicate-mark`.

---

## Ce qu'on ne teste pas

| Quoi | Pourquoi |
|---|---|
| `LiteLLMClient` directement | Testerait litellm/OpenRouter, pas notre code |
| `ChromaVectorStore` en unitaire | Testerait chromadb, pas notre code |
| La logique de routing du LLM | Dépend du modèle — on teste que le résultat du routing est bien utilisé |
| Les middlewares FastAPI intégrés (CORS, etc.) | Comportement du framework |

On teste **notre code** : que les interfaces sont bien appelées, que les résultats sont correctement propagés, que les exceptions sont correctement levées et rattrapées.
