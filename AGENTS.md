# AGENTS.md

## Overview
Emporio da Musica Agent: a customer-support chat agent for a music store (catalog, orders, store policies), built in Python.
Backend lives in `backend/` (uv project, package `emporio`); the agent answers in Brazilian Portuguese.
Full design: [docs/superpowers/specs/2026-11-05-emporio-agent-design.md](docs/superpowers/specs/2026-11-05-emporio-agent-design.md).

## Commands
Run from the repo root; all targets execute in `backend/`.
- `make setup`: install deps and pre-commit hooks.
- `make check`: lint + typecheck + import contracts + tests. Green before every commit, except the `(red)` commit of a TDD pair, where only the new test may fail.
- `make test`: pytest only.
- `make db`: start Postgres (host port 5434), migrate, ingest policies and products.
- `make test-pg`: Postgres integration tests on a separate `emporio_test` database; never touches dev data.
- `make evals [PROVIDER=gemma|gemini|openai|anthropic|local]`: retrieval eval plus the agent golden cases (real model) on `emporio_test`; not part of `make check`.
- `make chat [ARGS="--as-customer 14 --provider gemini"]`: interactive agent in the terminal (needs a provider key and Langfuse).
- `make mcp`: the store tools over MCP stdio; `EMPORIO_MCP_CUSTOMER_ID=14` fixes the identity, unset is anonymous. Needs no model key.
- `make langfuse-up`: local Langfuse (compose `observability` profile) at http://localhost:3000.
- `make fmt`: ruff format and `ruff check --fix`.
- `make up [PROVIDER=...]`: check config, DB, Langfuse, build the frontend, serve the web demo at http://localhost:8000. Needs `make web-keys` and `DEMO_EMAIL`/`DEMO_PASSWORD` in `.env`; `EMPORIO_FAKE_MODEL=1` swaps in the scripted model (no provider key).
- `make up PROVIDER=local`: Gemma 4 on this machine through Ollama. `make local-model` (`emporio local-model`) runs first: it picks the route (native on Apple Silicon, Docker with NVIDIA, Docker CPU) and the tag by memory, prints the download/memory/time warning, pulls the tag and creates `emporio-gemma` from a Modelfile with `num_ctx 16384`. `make dev` and `make evals` do the same with `PROVIDER=local`.
- `make dev`: the API with `--reload` on :8000 plus Vite (proxying `/api`).
- `make check-web`: frontend oxlint + Vitest + `tsc -b` + `vite build`.
- `make e2e [PROVIDER=...]`: Playwright browser flow against a real server; scripted model unless `PROVIDER` is given. Needs Docker; not part of `make check`.

## Architecture rules
Enforced by `import-linter` (`make imports`).

| Layer | May import |
|---|---|
| `*/domain` | only `shared` and stdlib. No LangChain, SQL, FastAPI or IO |
| `*/application` | own `domain`, other `application` via ports, `shared` |
| `*/infrastructure` | `application`, `domain` and external libs |
| `api/` | `support.application`, `support.domain`, `shared` and `config`; never an `infrastructure`, `bootstrap`, `db` or LangChain/psycopg/Langfuse (enforced) |
| `cli.py` | `bootstrap`, `config`, `local_model`, the `db` errors and `support.domain.channel_identity` (never an `infrastructure` module directly) |
| `web.py` | a composition root like `bootstrap`: `api`, `bootstrap`, `config` and `paths` |

`emporio.db`, `embeddings`, `migrate` are leaf technical modules usable only by infrastructure; The composition roots are `emporio.bootstrap` (the agent: wires use cases, tools, model, tracing) and `emporio.ingest` (the data: PDF and CSV into Postgres).

Domain has no IO and no frameworks. One use case per file.

## TDD
Red, green, refactor. Each behavior is a pair of commits: `test(x): <behavior> (red)` then `feat(x): <behavior>`, optionally `refactor(x)`.

## Commits & PRs
- Conventional Commits with the domain as scope: `feat(catalog): ...`, `docs(readme): ...`, `chore(repo): ...`, `ci: ...`.
- Subject at most 72 chars, imperative; body explains the why when not obvious.
- AI-assisted commits carry the `Co-Authored-By` trailer.
- One branch per milestone (`feat/catalog`, `feat/agent`, ...); PR with a short description; merge commit, no squash.
- Never force-push. Never rewrite `main`.

## Secrets
Never write keys or real values in any file. Use `.env` (git-ignored); `.env.example` lists names only.

## Language policy
- English: code, identifiers, commits, PRs, this file, skills, rules, and all engineering docs (`docs/**`, `.design/`).
- Portuguese (pt-BR): `README.md`, `examples/`, and everything the store's customer reads or that shapes the agent's Portuguese speech (agent responses, voice guide, persona prompts).
- The agent talks to customers in Brazilian Portuguese.

## Gotchas
- Files in `data/` have spaces and accents in their names; never hardcode them, use `emporio.paths`.
- `DATABASE_URL` is the only DB setting. `make db`, `make test-pg`, `make evals`, `make chat` and `make mcp` set their own URL; `make test`/`make check` ignore any exported `DATABASE_URL`; Postgres tests only run against a database whose name ends in `_test`.
- First use of the e5 embedder downloads about 470 MB (fastembed cache); `make db` and `make evals` need it.
- Langfuse is mandatory: `make chat` and `make evals` fail at startup without its keys, and first run `emporio check-config` so a missing provider key fails in seconds, before Docker starts. The `observability` profile needs about 2.3 GB RAM; the first `make langfuse-up` pulls images (about 7 min).
- `make db-up` (so `make db`) generates the Langfuse secrets into `.env` when absent; never print or commit them.
- `LLM_PROVIDER` defaults to gemma, which needs `VLLM_BASE_URL` and `VLLM_API_KEY`; other providers need their own `*_API_KEY`; `local` needs none (`OLLAMA_BASE_URL`, `OLLAMA_MODEL` have defaults). No silent fallback.
- `PROVIDER=local` triggers `local-model` for `make up`/`make dev` only when given on the command line (like `LLM_PROVIDER`), and for `make evals` whenever `PROVIDER=local`; `.env`'s `LLM_PROVIDER` never triggers it. Without the Modelfile's `num_ctx`, Ollama silently truncates the prompt and tools. Docker on macOS has no Metal, so Apple Silicon needs the native Ollama app.
- Web demo: on plain-http localhost set `SESSION_HTTPS_ONLY=false` or the browser drops the session cookie (`make up`, `make dev` and `make e2e` do it). `make e2e` needs Docker and Langfuse running.
- Web state is per process: rate limits, thread locks and the warm-up status live in memory; run one API process (one container on Modal) until they move to a shared store.
- Proxy: `make deploy-proxy` deploys the Cloudflare Worker; its secret is set once with `cd deploy/cloudflare && npx wrangler secret put PROXY_SECRET`, and the same value goes in the Modal secret `emporio-proxy` (key `PROXY_SECRET`) that `deploy/modal_api.py` needs for the non-loadtest app.
- Pre-commit does not typecheck: run `make check` before committing, not only the hooks.
- `data/` is read-only source material.

## Code style
Conventions no tool checks are in `.claude/rules/python-style.md`. The ruff and basedpyright (strict in domain/application/shared) gates are law: fix the code, do not silence them.
