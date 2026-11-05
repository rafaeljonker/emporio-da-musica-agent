export PATH := $(CURDIR)/backend/.venv/bin:$(PATH)

.PHONY: help setup fmt lint typecheck imports test check db-up db-test migrate db test-pg ingest evals
.DEFAULT_GOAL := help

help:
	@echo "targets: setup fmt lint typecheck imports test check db-up db-test migrate db test-pg ingest evals"

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
# Tests truncate tables, so they get their own database.
TEST_DATABASE_URL := postgresql://emporio:emporio@localhost:5434/emporio_test

db-up:
	docker compose up -d --wait db

db-test: db-up
	docker compose exec -T db psql -U emporio -d emporio -tc "SELECT 1 FROM pg_database WHERE datname='emporio_test'" | grep -q 1 || docker compose exec -T db createdb -U emporio emporio_test

migrate:
	cd backend && DATABASE_URL=$(DATABASE_URL) uv run python -m emporio.migrate

ingest:
	cd backend && DATABASE_URL=$(DATABASE_URL) uv run python -m emporio.ingest

# Always local: an exported DATABASE_URL (e.g. Railway) must not be migrated by accident.
db: db-up
	$(MAKE) migrate ingest DATABASE_URL=$(LOCAL_DATABASE_URL)

test-pg: db-up db-test
	cd backend && DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest -q -m "postgres and not eval"

evals: db-up db-test
	cd backend && DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest -q -m eval -s
