# src/application/agent/

Couche d'orchestration : reçoit un message utilisateur, décide s'il faut faire du RAG, génère la réponse via le LLM, persiste l'historique.

---

## Rôle dans l'architecture

```
API Layer (routes/chat.py)
    ↓ appelle
AgentGraph.invoke()
    ↓ utilise
ILLMClient  ·  RAGSearchTool  ·  ISessionStore
```

L'agent est instancié **une seule fois** au démarrage dans `create_app()` (`src/adapters/primary/api/main.py`) et stocké sur `app.state.agent`. Toutes les requêtes partagent la même instance.

---

## Fichiers

### `graph.py` — Orchestrateur principal

`AgentGraph` est une **classe procédurale** — pas un `StateGraph` LangGraph. LangGraph est listé comme dépendance mais n'est pas utilisé pour l'orchestration. Les trois étapes sont appelées séquentiellement via `await`.

#### Étapes du pipeline

```
invoke(message, session_id)
    │
    ├─ _route()         → LLM classifie : "RAG" ou "DIRECT"
    │
    ├─ _rag_search()    → (seulement si RAG) embed + recherche ChromaDB
    │
    └─ _generate()      → LLM génère avec historique + contexte
```

#### `_route(state)` → `AgentState`

Envoie le dernier message au LLM avec `ROUTE_PROMPT`. Attend la réponse `"RAG"` ou `"DIRECT"`. Positionne `state["used_retrieval"]`.

Décision prise par le LLM, pas par regex — peut varier selon le modèle. Ne pas supposer un comportement déterministe dans les tests : mocker `llm.complete` avec `side_effect`.

#### `_rag_search(state)` → `AgentState`

Appelle `RAGSearchTool.run(query)` qui embarque la query et interroge ChromaDB. Peuple `state["retrieved_docs"]`. Mesure la latence avec `retrieval_latency_seconds`.

#### `_generate(state)` → `AgentState`

Construit le prompt système en concaténant :
1. `GENERATE_PROMPT` (instructions de base)
2. Historique de la session (`ISessionStore.get_history`)
3. Documents récupérés (si RAG)

Appelle `ILLMClient.complete`. Persiste user + assistant dans le store. Mesure la latence avec `llm_latency_seconds`.

#### `invoke()` → `ChatResponse`

Point d'entrée public. Initialise l'`AgentState`, chaîne les trois étapes, met à jour `active_sessions`, construit et retourne le `ChatResponse`.

Le score de similarité des `Source` est fixé à `0.0` — ChromaDB retourne une distance mais elle n'est pas propagée dans `Chunk` pour l'instant.

#### Constantes prompt

```python
ROUTE_PROMPT   # Instructions de classification RAG/DIRECT
GENERATE_PROMPT  # Instructions de génération avec citation des sources
```

#### `build_agent()`

Fonction factory qui instancie `AgentGraph`. Utilisée dans `create_app()` pour séparer la construction de l'utilisation.

---

### `memory.py` — Session store en mémoire

Deux classes :

#### `ConversationMemory`

`deque` de taille maximale `max_turns * 2` (chaque tour = 1 message user + 1 message assistant). Quand la deque est pleine, le message le plus ancien est automatiquement éjecté.

```python
memory = ConversationMemory(max_turns=10)  # 20 messages max
memory.add(ChatMessage(role="user", content="..."))
history = memory.get_history()  # list[ChatMessage], ordre chronologique
```

#### `InMemorySessionStore`

Implémente `ISessionStore`. Dict `session_id → ConversationMemory`, créé à la demande. Les sessions ne sont jamais purgées — elles persistent jusqu'au redémarrage du process.

**Limite** : état perdu au redémarrage. Pour la persistance, configurer `POSTGRES_DSN` et utiliser `PostgresSessionStore` (`src/adapters/secondary/postgres_session_store.py`).

`is_healthy()` retourne toujours `True` — c'est intentionnel (pas de dépendance externe).

---

### `tools.py` — Outil RAG

#### `RAGSearchTool`

Encapsule la logique embed + search pour la rendre accessible à l'agent comme un "tool" nommé.

```python
tool = RAGSearchTool(vector_store, embedder)
result = await tool.run("ma query", top_k=5)
# result.chunks → list[Chunk]
# result.format() → str formatté pour le prompt LLM
```

#### `SearchResult`

Dataclass simple. `format()` produit un texte `[Source: …]\n<content>` séparé par `---` pour injection dans le prompt système.

---

## Ajouter un nouvel outil agent

1. Créer une classe avec `name`, `description`, et `async def run(...)` dans `tools.py`
2. L'injecter dans `AgentGraph.__init__()` et l'appeler dans `_rag_search()` ou une nouvelle étape
3. Mettre à jour le `ROUTE_PROMPT` si la classification doit tenir compte du nouvel outil

---

## Tests

Les mocks utilisés : `MockLLMClient`, `MockVectorStore`, `MockSessionStore` dans `tests/conftest.py`.

Quand `complete` est appelé plusieurs fois (route puis génération) :
```python
mock_llm.complete.side_effect = ["RAG", "voici la réponse"]
```

Ne pas utiliser `return_value` seul si l'agent appelle `complete` deux fois dans le même test.
