export PATH := $(CURDIR)/backend/.venv/bin:$(PATH)

.PHONY: help setup fmt lint typecheck imports test check db-up migrate db test-pg ingest evals
.DEFAULT_GOAL := help

help:
	@echo "targets: setup fmt lint typecheck imports test check db-up migrate db test-pg ingest evals"

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
	cd backend && uv run pytest -q

check: lint typecheck imports test

# Dev-only local URL (matches docker-compose.yml).
LOCAL_DATABASE_URL := postgresql://emporio:emporio@localhost:5434/emporio

db-up:
	docker compose up -d --wait db

migrate:
	cd backend && DATABASE_URL=$(LOCAL_DATABASE_URL) uv run python -m emporio.migrate

ingest:
	cd backend && DATABASE_URL=$(LOCAL_DATABASE_URL) uv run python -m emporio.ingest

db: db-up migrate ingest

test-pg:
	cd backend && DATABASE_URL=$(LOCAL_DATABASE_URL) uv run pytest -q -m postgres

evals:
	cd backend && DATABASE_URL=$(LOCAL_DATABASE_URL) uv run pytest -q -m eval -s
