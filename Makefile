.PHONY: install lint format format-check typecheck security test test-integration test-all run \
        docker-up docker-down docker-build pre-commit-run check \
        frontend-install frontend-dev frontend-build frontend-lint frontend-typecheck

install:
	uv sync
	uv run pre-commit install

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

format-check:
	uv run ruff format --check src/ tests/

typecheck:
	uv run mypy src/

security:
	uv run bandit -r src/ -ll

test:
	uv run pytest tests/unit/ -v --cov-fail-under=80

test-integration:
	uv run pytest tests/integration/ -v -m integration

test-all:
	uv run pytest tests/ -v --cov-fail-under=80

run:
	uv run uvicorn src.api.main:app --reload --port 8000

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-build:
	docker build -t enterprise-rag-agent:local .

pre-commit-run:
	uv run pre-commit run --all-files

check: lint format-check typecheck security test

# Frontend (Next.js 16) -------------------------------------------------------

frontend-install:
	cd frontend && npm ci

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

frontend-lint:
	cd frontend && npm run lint

frontend-typecheck:
	cd frontend && npx tsc --noEmit
