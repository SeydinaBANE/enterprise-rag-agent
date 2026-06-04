# Enterprise RAG Agent

Production-grade agentic RAG system built for enterprise knowledge management.

## Features

- **Autonomous LangGraph agent** — plans, reasons, and executes across tools
- **Document ingestion** — PDF, plain text, and web URLs into ChromaDB
- **Knowledge-grounded answers** — cited responses with source references
- **REST API** — FastAPI with API key auth and streaming support
- **Observability** — OpenTelemetry traces + Prometheus metrics + Grafana dashboards
- **Security guardrails** — PII detection, prompt injection protection, input validation
- **Production-grade CI/CD** — GitHub Actions, Docker image published to ghcr.io

## Quick Start

```bash
# 1. Install dependencies
make install

# 2. Configure environment
cp .env.example .env
# Edit .env: set OPENROUTER_API_KEY and API_KEY

# 3. Start infrastructure
make docker-up

# 4. Start API
make run
# → http://localhost:8000/docs
```

## Usage

### Ingest a document

```bash
curl -X POST http://localhost:8000/documents/ingest \
  -H "X-API-Key: your-api-key" \
  -F "file=@contract.pdf"
```

### Ask the agent

```bash
curl -X POST http://localhost:8000/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "What does the contract say about termination?", "session_id": "user-1"}'
```

## Documentation

| File | Description |
|---|---|
| [PLAN.md](PLAN.md) | Architecture decisions and design rationale |
| [PROJECT.md](PROJECT.md) | Project scope, goals, and stakeholders |
| [BUILD.md](BUILD.md) | Build and dependency management guide |
| [DEV.md](DEV.md) | Developer workflow and contribution guide |
| [DEPLOY.md](DEPLOY.md) | Deployment and operations guide |
| [CLI.md](CLI.md) | Full API and CLI reference |
| [TODO.md](TODO.md) | Roadmap and outstanding work |
| [docs/architecture.md](docs/architecture.md) | Architecture diagrams |
| [docs/adr/](docs/adr/) | Architecture Decision Records |

## Observability

| Service | URL |
|---|---|
| API docs | http://localhost:8000/docs |
| Metrics | http://localhost:8000/metrics |
| Grafana | http://localhost:3000 (admin/admin) |
| Prometheus | http://localhost:9090 |

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- Docker + Docker Compose
- OpenRouter API key

## License

MIT — see [LICENSE](LICENSE).
