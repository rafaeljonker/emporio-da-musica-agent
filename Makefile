export PATH := $(CURDIR)/backend/.venv/bin:$(PATH)

.PHONY: help setup fmt lint typecheck imports test check db-up db-test migrate db test-pg ingest evals langfuse-keys web-keys langfuse-db langfuse-up chat-config evals-config chat mcp deploy-llm deploy-api web-install web-build check-web up-preflight web-config local-model up dev e2e loadtest deploy-proxy
.DEFAULT_GOAL := help

help:
	@echo "targets: up dev e2e local-model setup fmt lint typecheck imports test check web-install web-build check-web db-up db-test migrate db test-pg ingest evals langfuse-keys web-keys langfuse-db langfuse-up chat-config evals-config chat mcp deploy-llm deploy-api deploy-proxy loadtest"

setup:
	cd backend && uv sync && uv run pre-commit install --config ../.pre-commit-config.yaml

fmt:
	cd backend && uv run ruff format . && uv run ruff check --fix .

# Outside backend/, linted with its config (CI runs the same list).
LINT_EXTRA = e2e deploy loadtest

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	ruff check --config backend/pyproject.toml $(LINT_EXTRA) && ruff format --config backend/pyproject.toml --check $(LINT_EXTRA)

typecheck:
	cd backend && uv run basedpyright

imports:
	cd backend && uv run lint-imports

test:
	cd backend && env -u DATABASE_URL uv run pytest -q

check: lint typecheck imports test

web-install:
	cd frontend && npm ci

web-build: web-install
	cd frontend && npm run build

# oxlint + Vitest + tsc -b and vite build (npm run build runs both).
check-web: web-install
	cd frontend && npm run lint && npm test && npm run build

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

# PROVIDER picks the model (gemma|gemini|openai|anthropic|local) and names backend/evals/reports/<provider>.md.
# EVAL_FAKE_MODEL=1 swaps in a scripted model to check the harness only (the gate then fails).
PROVIDER ?= gemma
# PROVIDER=local first picks, pulls and creates the Ollama model (warns about size and speed).
LOCAL_MODEL = $(if $(filter local,$(PROVIDER)),local-model,)

local-model:
	cd backend && uv run emporio local-model

# Fails in seconds on a missing provider key, before Docker, the database or Langfuse start.
evals-config:
	cd backend && LLM_PROVIDER=$(PROVIDER) uv run emporio check-config

evals: evals-config $(LOCAL_MODEL) db-test langfuse-up
	cd backend && LLM_PROVIDER=$(PROVIDER) DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest -q -m eval -s

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
	@chmod 600 .env

# Writes SESSION_SECRET into .env only when absent; the value is never printed.
web-keys:
	@touch .env
	@if [ -s .env ] && [ -n "$$(tail -c1 .env)" ]; then echo >> .env; fi
	@grep -q "^SESSION_SECRET=" .env || printf 'SESSION_SECRET=%s\n' "$$(openssl rand -hex 32)" >> .env
	@chmod 600 .env

# Langfuse shares our Postgres container but gets its own database.
langfuse-db: db-up
	docker compose exec -T db psql -U emporio -d emporio -tc "SELECT 1 FROM pg_database WHERE datname='langfuse'" | grep -q 1 || docker compose exec -T db createdb -U emporio langfuse

langfuse-up: langfuse-keys langfuse-db
	docker compose --profile observability up -d --wait

# ARGS example: make chat ARGS="--as-customer 14 --provider gemini"
chat-config:
	cd backend && uv run emporio check-config $(ARGS)

# Always the local database, like make db: an exported DATABASE_URL (e.g. Railway) is ignored.
chat: chat-config db langfuse-up
	cd backend && DATABASE_URL=$(LOCAL_DATABASE_URL) uv run emporio chat $(ARGS)

# MCP over stdio; EMPORIO_MCP_CUSTOMER_ID=14 fixes the identity (unset = anonymous).
mcp: db
	cd backend && DATABASE_URL=$(LOCAL_DATABASE_URL) uv run emporio mcp

up-preflight:
	@command -v docker >/dev/null || { echo "docker is required"; exit 1; }
	@docker info >/dev/null 2>&1 || { echo "the Docker daemon is not answering: start Docker Desktop and retry"; exit 1; }
	@command -v uv >/dev/null || { echo "uv is required"; exit 1; }
	@command -v node >/dev/null && node -e 'const [a, b] = process.versions.node.split(".").map(Number); process.exit(a > 22 || (a === 22 && b >= 12) ? 0 : 1)' || { echo "node >= 22.12 is required"; exit 1; }
	@echo "make up: 1) check config  2) database (Postgres :5434, migrate, ingest)"
	@echo "         3) Langfuse (first pull about 7 min, about 2.3 GB RAM)  4) build the frontend"
	@echo "         5) serve http://localhost:8000"

# PROVIDER on the command line overrides LLM_PROVIDER; otherwise .env's LLM_PROVIDER wins.
WEB_PROVIDER = $(if $(filter command line,$(origin PROVIDER)),LLM_PROVIDER=$(PROVIDER),)

# Like WEB_PROVIDER: only PROVIDER=local on the command line prepares the Ollama model.
WEB_LOCAL_MODEL = $(if $(filter command line,$(origin PROVIDER)),$(LOCAL_MODEL),)

# Provider key (skipped under EMPORIO_FAKE_MODEL=1), demo login and SESSION_SECRET (make web-keys).
web-config:
	cd backend && $(WEB_PROVIDER) uv run emporio check-config --web

# Plain http on localhost, so the session cookie is not https-only. Always the local database.
WEB_ENV = $(WEB_PROVIDER) SESSION_HTTPS_ONLY=false DATABASE_URL=$(LOCAL_DATABASE_URL)
SERVE = uv run uvicorn --factory emporio.web:create_web_app --port 8000

up: up-preflight web-config $(WEB_LOCAL_MODEL) db langfuse-up web-build
	cd backend && $(WEB_ENV) $(SERVE)

# API with --reload on :8000 plus Vite (proxying /api) in parallel; Ctrl-C stops both.
dev: web-config $(WEB_LOCAL_MODEL) db langfuse-up web-install
	(cd frontend && npm run dev) & cd backend && $(WEB_ENV) $(SERVE) --reload --reload-dir src

# Scripted model unless PROVIDER is given on the command line: make e2e PROVIDER=gemini.
E2E_FAKE = $(if $(filter command line,$(origin PROVIDER)),,EMPORIO_FAKE_MODEL=1 RATE_LIMIT_MULTIPLIER=10)

e2e: db langfuse-up web-build
	cd backend && uv run playwright install chromium
	$(E2E_FAKE) $(WEB_ENV) uv run --project backend pytest e2e -q

# Deploys the vLLM app emporio-llm-<gpu>-<weights> on Modal (costs GPU time once it is called).
LLM_GPU ?= H100
LLM_WEIGHTS ?= fp8
deploy-llm:
	cd backend && EMPORIO_GPU=$(LLM_GPU) EMPORIO_WEIGHTS=$(LLM_WEIGHTS) uv run modal deploy ../deploy/modal_llm.py

# Deploys emporio-api on Modal (CPU; calls LLM_APP's GPU). LOADTEST=1 deploys emporio-api-loadtest
# instead: scripted model, raised rate limits, no GPU. Run make deploy-llm first.
LLM_APP ?= emporio-llm-h100-fp8
LOADTEST ?=
# The hosted demo runs on Gemini (owner, 2026-11-06); API_PROVIDER=gemma uses the GPU app above.
API_PROVIDER ?= gemini
deploy-api: web-build
	cd backend && EMPORIO_API_PROVIDER=$(API_PROVIDER) EMPORIO_LLM_APP=$(LLM_APP) EMPORIO_LOADTEST=$(LOADTEST) uv run modal deploy ../deploy/modal_api.py

# Deploys the Cloudflare Worker emporio-proxy in front of emporio-api. The upstream URL is resolved
# at run time and redacted from wrangler's output; the Worker's PROXY_SECRET is set once with wrangler secret put.
deploy-proxy:
	@url=$$(cd backend && uv run python -c 'import modal; print(modal.Function.from_name("emporio-api", "web").get_web_url() or "")') && \
	[ -n "$$url" ] || { echo "emporio-api has no web URL: run make deploy-api first"; exit 1; }; \
	cd deploy/cloudflare && out=$$(npx wrangler deploy --var "UPSTREAM:$$url" 2>&1); rc=$$?; \
	printf '%s\n' "$$out" | sed "s#$$url#<upstream>#g"; exit $$rc

# Locust against a running app: make loadtest ARGS="--host <url> -u 50 -r 10 -t 2m". Needs DEMO_EMAIL and DEMO_PASSWORD.
loadtest:
	cd backend && uv run --group load locust -f ../loadtest/locustfile.py --headless $(ARGS)
