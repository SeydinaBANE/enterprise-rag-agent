# Developer Guide

## Git Workflow

```bash
git checkout -b feat/my-feature     # branch from main
# ... make changes ...
git add src/ tests/
git commit -m "feat: describe the change"   # triggers pre-commit hooks
git push origin feat/my-feature
# Open PR on GitHub → CI runs automatically
```

## Commit Convention

Format: `<type>(<scope>): <description>`

| Type | When to use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `chore` | Maintenance (deps, config) |
| `docs` | Documentation only |
| `test` | Tests only |
| `ci` | CI/CD changes |
| `refactor` | No behavior change |

Examples:
```
feat(rag): add MMR reranking to retriever
fix(api): handle empty query in chat endpoint
ci: add trivy scan to release workflow
test(agent): cover guardrail violation edge case
```

## Running Locally

```bash
make docker-up          # start ChromaDB, Prometheus, Grafana
make run                # hot-reload FastAPI at localhost:8000
```

## Running Tests

```bash
make test               # unit tests only (fast, no Docker needed)
make test-integration   # needs ChromaDB running (make docker-up first)
make test-all           # full suite

# Filter by name
uv run pytest -k "test_chat"

# With verbose output
uv run pytest tests/unit/ -v
```

## Observability in Dev

| Dashboard | URL |
|---|---|
| API docs (Swagger) | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Prometheus metrics | http://localhost:8000/metrics |
| Grafana | http://localhost:3001 (admin/admin) |
| Prometheus UI | http://localhost:9090 |

## Adding a New Agent Tool

1. Implement a tool class in `src/agent/tools.py` with a `run()` async method
2. Inject it in `AgentGraph.__init__()` in `src/agent/graph.py` and call it in `_rag_search()`
3. Add a unit test in `tests/unit/test_agent_graph.py`
4. Document the new behavior in `CLI.md` if it changes the API contract

## Adding a New Document Loader

1. Implement `IDocumentLoader` (from `src/core/ports.py`) in `src/rag/ingestion/loader.py`
2. Register the new loader in `src/rag/ingestion/pipeline.py`
3. Add unit tests and at least one edge case test

## Code Style

- Line length: 100 characters (enforced by ruff)
- Type hints: all parameters and return values (enforced by mypy strict)
- No `Any`, no `# type: ignore` without an explanation comment
- No comments explaining what the code does — only why (surprising constraints, workarounds)
- One function = one responsibility, max ~30 lines
