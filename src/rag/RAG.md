# src/rag/

Pipeline de Retrieval-Augmented Generation : ingestion de documents (chargement, découpage, embedding, stockage) et récupération de chunks pertinents à la requête.

---

## Vue d'ensemble

```
Ingestion (écriture)
─────────────────────────────────────────────────────────────────
source (fichier / URL)
    ↓ get_loader(source)
IDocumentLoader.load()     → list[Document]
    ↓ TextSplitter.split()
                           → list[Chunk]  (sans embedding)
    ↓ Embedder.embed()
                           → list[Chunk]  (avec embedding)
    ↓ IVectorStore.add_chunks()
ChromaDB


Récupération (lecture)
─────────────────────────────────────────────────────────────────
query (str)
    ↓ Embedder.embed_one()
                           → list[float]  (vecteur de la query)
    ↓ IVectorStore.search()
                           → list[Chunk]  (k chunks les plus proches)
```

---

## `embedder.py` — `Embedder`

Wrapper mince autour de `ILLMClient.embed()`. Délègue entièrement au client LLM, n'applique aucune logique propre.

```python
embedder = Embedder(llm_client)

# Batch — utilisé par IngestPipeline
embeddings = await embedder.embed(["texte 1", "texte 2"])   # list[list[float]]

# Unitaire — utilisé par RAGSearchTool et Retriever
embedding  = await embedder.embed_one("ma query")           # list[float]
```

`embed([])` retourne `[]` sans appeler le LLM.

---

## `retriever.py` — `Retriever`

Combine embedding et recherche vectorielle. Utilisé dans les intégrations directes (non passé par l'agent dans le flux actuel — l'agent passe par `RAGSearchTool`).

```python
retriever = Retriever(vector_store, embedder)
chunks = await retriever.search("ma question", top_k=5)
```

`top_k` par défaut = `settings.retrieval_top_k` (défaut 5).

---

## `ingestion/`

### `loader.py` — Chargeurs de documents

#### Dispatch — `get_loader(source: str) → IDocumentLoader`

| Source | Loader |
|---|---|
| `http://` ou `https://` | `URLLoader` |
| Extension `.pdf` | `PDFLoader` |
| Extension `.txt`, `.md`, `.rst` | `TextLoader` |
| Autre | `UnsupportedSourceError` |

#### `URLLoader`

1. Valide l'URL via `_validate_url()` (SSRF guard)
2. Télécharge avec `httpx` (timeout 15s, connect 5s, redirects suivis)
3. Parse le HTML avec BeautifulSoup — supprime `script`, `style`, `nav`, `footer`
4. Extrait le texte avec `get_text(separator="\n", strip=True)`

#### `PDFLoader`

Lit avec `pypdf.PdfReader`. Concatène les pages non vides avec `\n\n`. Retourne un seul `Document` par fichier.

#### `TextLoader`

Lit le fichier en UTF-8. Retourne un seul `Document` par fichier.

#### Guard SSRF — `_validate_url()` / `_is_private_host()`

Résout le hostname via DNS (`socket.getaddrinfo`) et vérifie que l'IP ne tombe pas dans un réseau privé :

| Réseau bloqué |
|---|
| `10.0.0.0/8` |
| `172.16.0.0/12` |
| `192.168.0.0/16` |
| `127.0.0.0/8` (loopback) |
| `169.254.0.0/16` (link-local) |
| `::1/128` (IPv6 loopback) |
| `fc00::/7` (IPv6 unique local) |

Si `ALLOWED_URL_DOMAINS` est non vide, seuls les hostnames se terminant par un domaine de la liste sont autorisés (en plus de la vérification d'IP privée).

#### Ajouter un nouveau format

1. Créer une classe qui hérite de `IDocumentLoader` dans `loader.py`
2. Implémenter `async def load(self, source: str) → list[Document]`
3. Ajouter le cas dans `get_loader()` (par extension ou préfixe)
4. Écrire les tests dans `tests/unit/test_rag_pipeline.py`

---

### `splitter.py` — `TextSplitter`

Découpage par mots (pas par tokens). Fenêtre glissante avec chevauchement.

```python
splitter = TextSplitter(chunk_size=512, chunk_overlap=50)
chunks = splitter.split(document)
```

Algorithme :
```
start = 0
while start < len(words):
    end = min(start + chunk_size, len(words))
    chunk = words[start:end]
    start = end - overlap   # recul de 'overlap' mots pour le prochain chunk
```

Chaque `Chunk` hérite du `document_id` et du `source` du `Document` parent. L'embedding est `[]` à ce stade — il sera rempli par `Embedder.embed()`.

Paramètres par défaut depuis `settings` : `max_chunk_size` (512) et `chunk_overlap` (50).

---

### `pipeline.py` — `IngestPipeline`

Orchestre les quatre étapes de l'ingestion en une seule méthode `run()`.

```python
pipeline = IngestPipeline(vector_store, embedder)
chunks = await pipeline.run("/path/to/file.pdf")
# ou
chunks = await pipeline.run("https://docs.example.com/page")
```

Étapes internes :
1. `get_loader(source)` → choisit le loader
2. `loader.load(source)` → `list[Document]`
3. `splitter.split(doc)` pour chaque document → `list[Chunk]` (sans embedding)
4. `embedder.embed([c.content for c in chunks])` → `list[list[float]]`
5. Affecte `chunk.embedding = embedding` pour chaque chunk
6. `vector_store.add_chunks(chunks)` → stockage dans ChromaDB

Retourne la liste complète des chunks stockés. Retourne `[]` si le document est vide après chargement et découpage.

Le `TextSplitter` est injectable au constructeur — utile pour les tests (passer un splitter avec de petits chunks sans toucher aux settings).
