.PHONY: install lint format typecheck security test run docker-up docker-down docker-build pre-commit-run

install:
	uv sync
	uv run pre-commit install

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

typecheck:
	uv run mypy src/

security:
	uv run bandit -r src/ -ll

test:
	uv run pytest tests/unit/ -v

test-integration:
	uv run pytest tests/integration/ -v

test-all:
	uv run pytest tests/ -v

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

check: lint typecheck security test
