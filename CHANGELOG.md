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
- OpenTelemetry tracing and Prometheus metrics
- Native security guardrails (PII detection, prompt injection)
- Multi-stage Dockerfile for production
- Docker Compose stack with ChromaDB, Prometheus, Grafana
- GitHub Actions CI pipeline (lint, typecheck, security, test)
- GitHub Actions release pipeline (build + Trivy scan + push to ghcr.io)
- Pre-commit hooks (ruff, mypy, commitlint)
- Full documentation (README, PLAN, PROJECT, BUILD, DEV, DEPLOY, CLI, TODO)
- Architecture Decision Records (ADR 001–003)

## [0.1.0] — TBD

Initial MVP release.
