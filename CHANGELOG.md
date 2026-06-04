# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project scaffold with Clean Architecture
- LangGraph agent with RAG retrieval and tool use
- Document ingestion pipeline (PDF, text, URL)
- ChromaDB vector store integration via OpenRouter/litellm
- FastAPI REST API with API key authentication
- Prometheus metrics with HTTP request duration histogram
- Native security guardrails (PII detection, prompt injection)
- Multi-stage Dockerfile for production
- Docker Compose stack with ChromaDB, Prometheus, Grafana
- GitHub Actions CI pipeline (lint, typecheck, security, test)
- GitHub Actions release pipeline (build + Trivy scan + push to ghcr.io)
- Pre-commit hooks (ruff, mypy)
- Architecture Decision Records (ADR 001–003)

### Changed
- LLM client: configurable timeout (default 60s) with exponential retry (max 2)
- LLM healthcheck: replaced paid `acompletion("ping")` with lightweight HEAD request
- ChromaDB: dimension mismatch guard on ingest, `ingested_at` stored in metadata
- File uploads: max 50 MB limit enforced (HTTP 413)
- URL ingestion: SSRF guard blocks private IPs, supports domain allowlist via `ALLOWED_URL_DOMAINS`
- CORS default restricted to `["http://localhost:3000"]`
- Rate limiting: proxy-aware IP detection (X-Forwarded-For, X-Real-IP)
- Postgres pool: configurable `POSTGRES_POOL_MIN` (2) and `POSTGRES_POOL_MAX` (10)
- Session store: logs warning when using in-memory (no `POSTGRES_DSN`)
- Removed dead OpenTelemetry configuration

## [0.1.0] — TBD

Initial MVP release.
