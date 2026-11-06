export PATH := $(CURDIR)/backend/.venv/bin:$(PATH)

.PHONY: help setup fmt lint typecheck imports test check db-up db-test migrate db test-pg ingest evals langfuse-keys langfuse-db langfuse-up chat mcp
.DEFAULT_GOAL := help

help:
	@echo "targets: setup fmt lint typecheck imports test check db-up db-test migrate db test-pg ingest evals langfuse-keys langfuse-up chat"

setup:
	cd backend && uv sync && uv run pre-commit install --config ../.pre-commit-config.yaml

fmt:
	cd backend && uv run ruff format . && uv run ruff check --fix .

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .

typecheck:
	cd backend && uv run basedpyright

imports:
	cd backend && uv run lint-imports

test:
	cd backend && env -u DATABASE_URL uv run pytest -q

check: lint typecheck imports test

# Dev-only local URL (matches docker-compose.yml); callers may override DATABASE_URL (e.g. Railway).
LOCAL_DATABASE_URL := postgresql://emporio:emporio@localhost:5434/emporio
DATABASE_URL ?= $(LOCAL_DATABASE_URL)
# Exported so recipes do not echo the URL (it may carry a password).
export DATABASE_URL
# Tests truncate tables, so they get their own database.
TEST_DATABASE_URL := postgresql://emporio:emporio@localhost:5434/emporio_test

db-up: langfuse-keys
	docker compose up -d --wait db

db-test: db-up
	docker compose exec -T db psql -U emporio -d emporio -tc "SELECT 1 FROM pg_database WHERE datname='emporio_test'" | grep -q 1 || docker compose exec -T db createdb -U emporio emporio_test

migrate:
	cd backend && uv run python -m emporio.migrate

ingest:
	cd backend && uv run python -m emporio.ingest

# Always local: an exported DATABASE_URL (e.g. Railway) must not be migrated by accident.
db: db-up
	$(MAKE) migrate ingest DATABASE_URL=$(LOCAL_DATABASE_URL)

test-pg: db-up db-test
	cd backend && DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest -q -m "postgres and not eval"

evals: db-up db-test
	cd backend && DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest -q -m eval -s

# Writes the Langfuse secrets into .env only when absent; values are never printed.
langfuse-keys:
	@touch .env
	@if [ -s .env ] && [ -n "$$(tail -c1 .env)" ]; then echo >> .env; fi
	@put() { grep -q "^$$1=" .env || printf '%s=%s\n' "$$1" "$$2" >> .env; }; \
	hex() { openssl rand -hex "$$1"; }; \
	pk="pk-lf-$$(hex 16)"; sk="sk-lf-$$(hex 16)"; \
	put SALT "$$(hex 16)"; put ENCRYPTION_KEY "$$(hex 32)"; put NEXTAUTH_SECRET "$$(hex 32)"; \
	put CLICKHOUSE_PASSWORD "$$(hex 16)"; put MINIO_ROOT_PASSWORD "$$(hex 16)"; put REDIS_AUTH "$$(hex 16)"; \
	put LANGFUSE_INIT_ORG_ID emporio; put LANGFUSE_INIT_ORG_NAME Emporio; \
	put LANGFUSE_INIT_PROJECT_ID emporio-agent; put LANGFUSE_INIT_PROJECT_NAME emporio-agent; \
	put LANGFUSE_INIT_PROJECT_PUBLIC_KEY "$$pk"; put LANGFUSE_INIT_PROJECT_SECRET_KEY "$$sk"; \
	put LANGFUSE_INIT_USER_EMAIL admin@emporio.local; put LANGFUSE_INIT_USER_NAME admin; \
	put LANGFUSE_INIT_USER_PASSWORD "$$(hex 12)"; \
	put LANGFUSE_PUBLIC_KEY "$$pk"; put LANGFUSE_SECRET_KEY "$$sk"; \
	put LANGFUSE_BASE_URL http://localhost:3000; put LANGFUSE_SALT "$$(hex 16)"

# Langfuse shares our Postgres container but gets its own database.
langfuse-db: db-up
	docker compose exec -T db psql -U emporio -d emporio -tc "SELECT 1 FROM pg_database WHERE datname='langfuse'" | grep -q 1 || docker compose exec -T db createdb -U emporio langfuse

langfuse-up: langfuse-keys langfuse-db
	docker compose --profile observability up -d --wait

# ARGS example: make chat ARGS="--as-customer 14 --provider gemini"
chat: db langfuse-up
	cd backend && uv run emporio chat $(ARGS)

# MCP over stdio; EMPORIO_MCP_CUSTOMER_ID=14 fixes the identity (unset = anonymous).
mcp: db
	cd backend && uv run emporio mcp
