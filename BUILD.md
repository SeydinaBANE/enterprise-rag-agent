# Build Guide

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.12+ | https://python.org |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker | 24+ | https://docker.com |
| Git | 2.40+ | https://git-scm.com |

## Local Setup

```bash
git clone https://github.com/<user>/enterprise-rag-agent
cd enterprise-rag-agent

# Install all dependencies + pre-commit hooks
make install

# Configure environment
cp .env.example .env
# Edit .env: set OPENROUTER_API_KEY and API_KEY
```

## Dependency Management

```bash
# Add a production dependency
uv add <package>

# Add a dev dependency
uv add --group dev <package>

# Sync from lockfile (after pulling)
uv sync

# Update all dependencies
uv lock --upgrade
uv sync
```

## Build Docker Image

```bash
# Local build
make docker-build
# → enterprise-rag-agent:local

# Run local image
docker run --env-file .env -p 8000:8000 enterprise-rag-agent:local
```

## Quality Gates

All 5 must pass before any commit (enforced by pre-commit and CI):

```bash
make lint          # ruff — zero linting errors
make format-check  # ruff format --check — no formatting drift
make typecheck     # mypy strict — zero type errors
make security      # bandit — no HIGH/CRITICAL findings
make test          # pytest — all green, coverage ≥ 80%
```

Shortcut to run all:

```bash
make check
```

## Project Layout

```
src/domain/                Domain models, exceptions, config — zero ext deps
src/ports/                 Inbound (use-case) and outbound (driven) port ABCs
src/adapters/secondary/    ChromaDB, litellm, Postgres, loaders — driven adapters
src/application/rag/       Document ingestion, embedding, and retrieval pipeline
src/application/agent/     AgentGraph (plain class): tools, memory, invoke pipeline
src/guardrails/            Input/output safety filters
src/observability          OpenTelemetry + Prometheus instrumentation
src/adapters/primary/api/  FastAPI application: routes, middleware, app factory
tests/unit/                Fast, fully mocked unit tests
tests/integration/         Real ChromaDB, mocked LLM
```
