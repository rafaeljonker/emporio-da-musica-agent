.PHONY: help setup fmt lint typecheck imports test check
.DEFAULT_GOAL := help

help:
	@echo "targets: setup fmt lint typecheck imports test check"

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
