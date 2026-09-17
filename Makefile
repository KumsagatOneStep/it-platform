.PHONY: up down test lint format openapi migrate create-admin

up:
	docker compose up -d postgres redis

down:
	docker compose down

test:
	cd backend && uv run pytest -q

lint:
	cd backend && uv run ruff format --check . && uv run ruff check . && uv run mypy app tests && uv run lint-imports

format:
	cd backend && uv run ruff format . && uv run ruff check --fix .

openapi:
	cd backend && uv run python -m app.scripts.export_openapi openapi.json

migrate:
	cd backend && uv run alembic upgrade head

create-admin:
	cd backend && uv run python -m app.cli create-admin --email "$(EMAIL)" --full-name "$(NAME)"
