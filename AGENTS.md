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
- `make ingest` reseeds the catalog from the CSVs and deletes the products demo users created (the manual reset after an evaluation); orders stay on CSV.
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
- `make deploy-llm [LLM_GPU=H100|L40S] [LLM_WEIGHTS=fp8|bf16]`: vLLM Gemma app `emporio-llm-<gpu>-<weights>` on Modal (paid GPU).
- `make deploy-api [API_PROVIDER=gemini|gemma] [LLM_APP=...] [LOADTEST=1]`: the web API on Modal; defaults to Gemini (the hosted demo), `gemma` calls the GPU app, `LOADTEST=1` deploys the fake-model `emporio-api-loadtest`.
- `make deploy-proxy`: the Cloudflare Worker in front of `emporio-api` (emporio.fastmind.site).
- `make loadtest ARGS="--host <url> -u 50 -r 10 -t 2m"`: Locust against a deployed app; only against `emporio-api-loadtest` (fake model). Results: `docs/scaling-and-cost.md`.
- `make loadtest-down`: stops `emporio-api-loadtest`; run it after every load test (it shares the demo's secrets and database, with 100x rate limits).

## Architecture rules
Enforced by `import-linter` (`make imports`).

Folder map (`backend/src/emporio/`):
- `catalog/`, `orders/`, `policies/`, `support/`: bounded contexts, each `domain/`, `application/`, `infrastructure/`. The agent tools live in `support/infrastructure/agent/tools/` (one module per context plus `base`).
- `shared/`: `Money`, the `Clock` port, `Result`, `StoreUnavailable`.
- `api/`: the FastAPI routes and `errors.py` (code → HTTP).
- `platform/`: technical modules: `config/` (settings, checks, MCP tokens, errors), `db`, `embeddings`, `migrate`, `paths`, `local_model`, the system clock.
- `entrypoints/`: composition roots: `bootstrap` (the agent: use cases, tools, model, tracing), `web` (the uvicorn factory), `cli` (`emporio` command), `ingest` (PDF and catalog CSV seed into Postgres).
- Where runtime state lives: [docs/architecture/state.md](docs/architecture/state.md).

| Layer | May import |
|---|---|
| `*/domain` | only `shared` and stdlib. No LangChain, SQL, FastAPI or IO |
| `*/application` | own `domain`, other `application` via ports, `shared` |
| `*/infrastructure` | `application`, `domain`, `platform` and external libs |
| `api/` | `support.application`, `support.domain`, `catalog.application.admin`, the `catalog.domain.errors` enum, `shared` and `platform.config`; never another `domain` or `application`, an `infrastructure`, `entrypoints`, `platform.db/migrate/embeddings` or LangChain/psycopg/Langfuse (direct imports, enforced) |
| `platform/` | external libs and itself; never a context (enforced) |
| `entrypoints/` | anything: they wire the contexts, `api` and `platform`; nothing imports them |

Domain has no IO and no frameworks. One use case per file.

Errors (ADRs [0013](docs/decisions/0013-domain-errors-as-values.md), [0014](docs/decisions/0014-error-mapping-at-the-boundaries.md), rule `.claude/rules/backend-errors.md`):
- Expected failures return `Result` (`Ok` / `Err`) with a context's `StrEnum` code from `<ctx>/domain/errors.py`; exceptions are for the unexpected.
- Each boundary maps a code once, exhaustively (`assert_never`): `api/errors.py` to HTTP, `agent/tools/<ctx>.py` to pt-BR text. Unexpected API errors answer 500 `{"detail": "internal_error"}`.
- No code decides on an error message.

Tests mirror the source: `backend/tests/<ctx>/<layer>/`, plus `api/`, `platform/`, `entrypoints/`, `evals/`. Builders live in `tests/<ctx>/fakes.py` (`make_box` in `tests/support/fakes.py`), API clients in `tests/api/helpers.py`, context-free fakes in `tests/fakes/`; never import another test module or a conftest. Markers (`--strict-markers`): `postgres` (`make test-pg`), `eval` (`make evals`), `files` (real `data/` files, no DB), `contract` (tool and MCP schemas); unit tests are unmarked.

### Frontend
Folder map (`frontend/src/`; ADR [0015](docs/decisions/0015-frontend-domain-folders-and-view-models.md), rule `.claude/rules/frontend-view-models.md`):
- `app/`: bootstrap (`main.tsx`, `index.css`) and `App.tsx` + `useApp.ts` (the session).
- `client/<domain>/` for `auth`, `catalog`, `chat`, `warmup`: `domain/` (pure TS rules, no React, no IO), `ui/` (hookless presentation, typed props), `useCases/<case>/` (`Component.tsx` beside `use{Component}.ts` and its data hooks), `__tests__/`.
- `client/shared/`: `components/ui/` (shadcn primitives, visually untouched), `lib/` (`api.ts`, `apiTypes.ts`, `copy.ts`, `errorMessage.ts`, `session.ts`, `focus.ts`), `assets/`.
- `shared/result.ts`: `Result<T, E> = { ok: true; data } | { ok: false; error }`. `test-support/`: Vitest setup, fixtures, fetch/SSE stubs.

View-model rules (oxlint fences the hooks and the domain imports):
- A use-case component makes exactly one hook call, `use{Component}(props)`, destructures it and renders. No `useState`/`useEffect`/`useMemo`/`useCallback`/`useForm` in its body; a JSX arrow only adapts arguments.
- The view model returns a discriminated union (`state`), every variant declaring every field it renders.
- Data hooks are single-purpose and return `pending | error{error} | success{data}`; no toast, navigation or session handling.
- Effects only sync with outside systems (fetch, timers, DOM listeners, storage); side effects run in event handlers.
- The HTTP client never throws: every endpoint returns `Result<T, ApiError>`. `errorMessage.ts` is the only place a code becomes text. A 401 outside login calls `notifySessionExpired()`; `useApp` signs out.
- The catalog form is React Hook Form + `zodResolver(productSchema)`: the schema owns every rule and message; validation runs on submit; server codes go through `setError`.
- Tests: `renderHook` for hooks with real behavior, fetch stubbed (never our own modules mocked); fast-check for pacing and the queue; no component tests (the e2e pins the markup).

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
- Files in `data/` have spaces and accents in their names; never hardcode them, use `emporio.platform.paths`.
- `DATABASE_URL` is the only DB setting. `make db`, `make test-pg`, `make evals`, `make chat` and `make mcp` set their own URL; `make test`/`make check` ignore any exported `DATABASE_URL`; Postgres tests only run against a database whose name ends in `_test`.
- First use of the e5 embedder downloads about 470 MB (fastembed cache); `make db` and `make evals` need it.
- Langfuse is mandatory: `make chat` and `make evals` fail at startup without its keys, and first run `emporio check-config` so a missing provider key fails in seconds, before Docker starts. The `observability` profile needs about 2.3 GB RAM; the first `make langfuse-up` pulls images (about 7 min).
- `make db-up` (so `make db`) generates the Langfuse secrets into `.env` when absent; never print or commit them.
- `LLM_PROVIDER` defaults to gemma, which needs `VLLM_BASE_URL` and `VLLM_API_KEY`; other providers need their own `*_API_KEY`; `local` needs none (`OLLAMA_BASE_URL`, `OLLAMA_MODEL` have defaults). No silent fallback.
- `PROVIDER=local` triggers `local-model` for `make up`/`make dev` only when given on the command line (like `LLM_PROVIDER`), and for `make evals` whenever `PROVIDER=local`; `.env`'s `LLM_PROVIDER` never triggers it. Without the Modelfile's `num_ctx`, Ollama silently truncates the prompt and tools. Docker on macOS has no Metal, so Apple Silicon needs the native Ollama app.
- Web demo: on plain-http localhost set `SESSION_HTTPS_ONLY=false` or the browser drops the session cookie (`make up`, `make dev` and `make e2e` do it). `make e2e` needs Docker and Langfuse running.
- Web state is per process: rate limits, thread locks and the warm-up status live in memory; run one API process (one container on Modal) until they move to a shared store.
- Proxy: `make deploy-proxy` deploys the Cloudflare Worker; its secret is set once with `cd deploy/cloudflare && npx wrangler secret put PROXY_SECRET`, and the same value goes in the Modal secret `emporio-proxy` (key `PROXY_SECRET`) that `deploy/modal_api.py` needs for the non-loadtest app.
- Remote MCP: `/mcp` is served only when `MCP_TOKENS` is set (Modal secret `emporio-mcp`, demo app only): comma-separated `token=identity`, identity a customer id or `anon`, tokens 32+ chars. Rotate by replacing the secret's value and redeploying (`make deploy-api`); never log or commit a token.
- Paid steps: `make deploy-llm`, any request that wakes the GPU app, `make evals PROVIDER=gemma` and `deploy/cold_start.py` spend Modal credit; ask the owner first and stop GPU containers afterwards.
- Never recreate the Modal secret `emporio-langfuse`: its `LANGFUSE_SALT` keys the trace pseudonyms.
- The API image sets `HF_HUB_OFFLINE=1` with e5 baked in: a change to the embedder needs a redeploy, never a runtime download.
- Pre-commit does not typecheck: run `make check` before committing, not only the hooks.
- `data/` is read-only source material.

## Code style
Conventions no tool checks are in `.claude/rules/python-style.md`. The ruff and basedpyright (strict in domain/application/shared) gates are law: fix the code, do not silence them.
