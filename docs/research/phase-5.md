# Phase 5 research: API, frontend, warm-up, `make up`, e2e

Date: 2026-11-05. Versions fetched that day from `https://pypi.org/pypi/<name>/json` and `https://registry.npmjs.org/<name>/latest`. Library behaviour was checked against official docs or source on GitHub `main` the same day; anything not verified is marked "unconfirmed". Local facts cite repo paths. Binding UI contract: `.design/projects/emporio-chat/design/` (screens 01–03, `shared/*`) and `.design/branding/emporio-da-musica/patterns/`.

| Package | Version | Note |
|---|---|---|
| fastapi | 0.162.0 (2026-10-23) | native SSE since 0.135.0 (`fastapi.sse`) |
| starlette | 1.10.0 | `SessionMiddleware` (signed cookie) |
| itsdangerous | 2.2.0 | imported by `starlette.middleware.sessions`; must be a direct dep |
| uvicorn | 0.54.0 | ASGI server |
| sse-starlette | 3.6.0 | not needed (FastAPI has it built in) |
| slowapi | 0.1.10 | not needed (see §2) |
| playwright / pytest-playwright | 1.64.1 / 0.10.0 | Python e2e (§7) |
| httpx | 0.28.1 | `TestClient` transport |
| modal | 1.6.3 | phase 6 deploy |
| vite / create-vite | 8.3.6 / 9.3.4 | template pins `typescript ~7.0.2`, `@vitejs/plugin-react ^6.1.2`, oxlint |
| react | 19.3.1 | |
| typescript | 7.0.2 (2026-07-08) | the native (Go) compiler line; see Risks |
| tailwindcss / @tailwindcss/vite | 4.3.4 | CSS-first config |
| shadcn (CLI) | 4.23.0 | Tailwind v4 + React 19 |
| radix-ui / tw-animate-css | 1.8.1 / 1.4.0 | pulled by shadcn |
| @fontsource-variable/fraunces / source-sans-3 | 5.3.0 / 5.3.1 | self-hosted fonts |
| lucide-react | 1.69.0 | icons |
| eventsource-parser | 4.1.3 (2026-10-25) | SSE parsing over `fetch` |
| @microsoft/fetch-event-source | 2.0.1 (2021-04-25) | unmaintained; skip |
| vitest / @testing-library/react / jsdom | 5.1.0 / 16.3.3 / 31.0.0 | |

## 1. `/chat` over SSE and how bubbles leave the server
- **FastAPI native SSE** (https://fastapi.tiangolo.com/tutorial/server-sent-events/): `from fastapi.sse import EventSourceResponse, ServerSentEvent`; `@app.post(..., response_class=EventSourceResponse)`; yield `ServerSentEvent(data=..., event="bubble")`. POST is supported. A plain `def` generator "runs so it doesn't block the event loop" (threadpool). Built in: 15 s keep-alive ping comment, `Cache-Control: no-cache`, `X-Accel-Buffering: no`. Disconnect handling is not documented. So `sse-starlette` adds nothing here.
- **Our stack is sync** (`GraphRunner.run` calls `graph.invoke`, psycopg pools). A sync generator fits without `AsyncPostgresSaver` (phase 4 research §1 said the same).
- **LangGraph streaming** (https://docs.langchain.com/oss/python/langgraph/streaming): `stream_mode="messages"` yields `(message_chunk, metadata)`; filter on `metadata["langgraph_node"] == "agent"`. `version="v2"` (LangGraph ≥ 1.1) yields `StreamPart` dicts `{type, ns, data}`; multiple modes via a list.
- **Two ways to produce bubbles:**
  - **(A) invoke, then emit.** Keep `HandleMessage` as is; when the `Reply` is ready emit `bubble` × n with `delay_ms`, then `metrics`, then `done`. Zero graph changes. The design already assumes it: "Bubble 1: `delay_ms = 0`. The typing indicator has been visible for the whole generation" (`shared/micro-interactions.md`).
  - **(B) token streaming.** Buffer agent-node text; emit a bubble each time `\n\n` closes one. Bubble 1 lands earlier by the time it takes to generate bubbles 2–3 (roughly 1–2 s on Gemma, unmeasured). Costs: skip chunks that carry `tool_call_chunks` (a model can write a preamble before calling a tool, which would leak a bubble); the `abuse_reply` node and `CHAT_ERROR` are not LLM output, so reconcile against the final `split_bubbles` at the end; `MAX_BUBBLES = 3` merging means bubble 3 is only known at the end; `ai_tells` and metrics are end-of-turn anyway. Bubbles 2–3 are paced 700–2400 ms after bubble 1, so streaming helps bubble 1 only.
- **Pacing lives in the backend** (design contract): `delay_ms` = 0 for bubble 1, then `clamp(400 + 22 × chars, 700, 2400)`, total cap 3000 ms. A pure function next to `split_bubbles` in `support/domain/bubbles.py`, unit-tested.
- **Disconnects:** with (A) the whole turn runs inside the first `next()` of the generator in a worker thread. A client disconnect stops later yields, never the turn: the checkpoint and `turn_metrics` stay consistent. With (B) the turn must run in its own thread that feeds a queue, or a disconnect can leave a half-written turn (the R9 failure mode, §9).
- **Per-thread lock:** a `dict[str, Lock]` with a non-blocking `acquire`; when busy, answer 409 and the UI keeps its "send disabled while streaming" rule. In-process only: if the API runs in more than one Modal container, swap for `pg_try_advisory_lock(hashtext(thread_id))` (works across containers, same pool). Mark it with a `ponytail:` comment.
- **Event contract** (closes PR-2 verdict rows 9–10): `typing {}` → `bubble {kind: "text", text, delay_ms}` → `metrics {...}` → `done {trace_id}`; `error {partial: bool}`. `kind` reserves `product | handoff` (§ decisions). `metrics` units are explicit: `input_tokens, output_tokens` (int), `ms_model, ms_guard, ms_llm, ms_tools` (int ms; `ms_model` = server `ms_total`), `cost_brl` (decimal string or `null`), `cost_basis` (string), `action` (pt-BR word from a tool-name map: `search_products` → "busca no catálogo", none → "sem ferramenta"). "Na tela" time is measured by the client.
- **Request:** `{text: str}` with 1–1000 chars; identity never comes from the body (§4).

**Recommendation:** native `EventSourceResponse` over a sync generator, option (A) invoke-then-emit with backend `delay_ms`, an in-process per-thread lock answering 409, and the event contract above written into the spec.

## 2. Demo auth
- **One demo user** from env (`DEMO_EMAIL`, `DEMO_PASSWORD`, `SESSION_SECRET`), compared with `hmac.compare_digest` on both fields. No user table, no hashing service: there is one credential and it lives in Modal secrets and `.env` (spec §5).
- **Session:** Starlette `SessionMiddleware(secret_key, max_age, same_site="lax"|"strict", https_only=True)`; it always sets `httponly`, signs with `itsdangerous.TimestampSigner`, and is "readable but not modifiable" (https://starlette.dev/middleware/, source `starlette/middleware/sessions.py`). Store only `{auth: true, sid, customer_id}`; nothing secret goes in it. JWT buys nothing for one same-origin client and needs revocation thinking; skip it.
- **CSRF:** same origin, no CORS middleware, `SameSite` cookie, and JSON-only bodies (reject non-`application/json` with 415 so a cross-site form post cannot be a "simple request"). Logout is `POST`. Whether FastAPI 0.162 already rejects a non-JSON content type on a model body is unconfirmed, so check it explicitly in a dependency.
- **Rate limiting:** a ~15-line in-memory sliding window (deque per key) for `/auth/login` (per IP, e.g. 5/min) and `/chat` (per session, e.g. 20 per 10 min, a GPU cost guard). slowapi is a new dependency for that. On Modal the client IP may be the proxy's; whether `X-Forwarded-For` is set is unconfirmed, so key login on IP **and** a global cap.
- **Never log credentials:** no request-body logging, the uvicorn access log has paths only, the 401 log line carries no e-mail. `SESSION_SECRET` and `DEMO_*` enter `.env.example` as names only; gitleaks already runs.
- **Login triggers warm-up server-side:** the login handler calls `warm.start()` and returns the warm status object in the response (screen 03 contract), so there is no separate client round trip; `POST /warm` stays for "Tentar de novo". `/warm` requires a session (no GPU spend for anonymous visitors, spec §5).

**Recommendation:** env single user + `SessionMiddleware` cookie (HttpOnly, Secure, SameSite) + JSON-only + a tiny in-memory limiter; login starts the warm-up and returns its status.

## 3. Warm-up contract and real readiness signals
- **Payload** (screen 02 + PR-2 rows 8, 15): `{mode: "modal_gpu"|"local_cpu"|"provider_api", stage: "server_starting"|"model_loading"|"ready"|"failed", started_at (ISO 8601 UTC), elapsed_seconds (server-computed, fixes clock skew), expected_seconds (p75 per mode from config), reply_p50_seconds (from `turn_metrics`, nullable)}`. Use the design's mode names (`modal_gpu`, not `gemma_gpu`). `reply_p50_seconds` templates the "uns 2 s" copy (PR-2 row 15): `percentile_cont(0.5)` over recent `ms_total`.
- **Mode** follows the provider: gemma → `modal_gpu`, gemini/openai/anthropic → `provider_api` (stage `ready` at once, `started_at` = now), Ollama → `local_cpu`.
- **vLLM:** `GET /health` returns 200, or 503 when the engine is dead (source `vllm/entrypoints/serve/instrumentator/health.py`); `/v1/models` also exists (https://docs.vllm.ai/en/latest/serving/online_serving/). Whether `/health` is exempt from `--api-key` is unconfirmed: send the bearer anyway. Derive the health URL from `VLLM_BASE_URL` minus `/v1`.
- **Modal cold start:** web functions have a 150 s request limit, after which Modal answers 303 to a result URL (https://modal.com/docs/guide/webhook-timeouts). The measured cold start is 175 s, so the probe must treat 303/timeout as "still starting" and retry until a deadline (e.g. 10 min → `failed`). Run it in one background thread per process (single-flight), never in the request.
- **Two GPU stages are not observable from outside:** vLLM opens its port only after the weights load, so a health probe sees "not ready" then "ready". Options: (a) show only `server_starting` until ready; (b) read `modal.Function.from_name(...).get_current_stats()` (returns `FunctionCurrentStats`, fields not documented: unconfirmed, https://modal.com/docs/reference/modal.Function) and switch to `model_loading` when a container is running. The design forbids advancing a stage on a timer.
- **E5 and DB:** both load in the API lifespan (`build_agent` applies migrations, builds pools); the API only answers once they are ready, so they are not a warm stage. Baking E5 into the image is phase 6 (§7.2.3).
- **Ollama (`local_cpu`):** OpenAI-compatible at `/v1`; `GET /api/ps` lists loaded models and an empty `/api/generate` loads one (https://docs.ollama.com/api, unconfirmed for the current release). `PROVIDER=local` does not exist in `config.py` yet.
- **State:** a module-level warm state per process. If the API scales past one container, `started_at` can differ between polls; a one-row Postgres table fixes it.

**Recommendation:** login starts a single-flight background probe of `/health` (303 and timeouts mean "starting"), the status carries server `elapsed_seconds` and config `expected_seconds`, and GPU stages come only from real signals.

## 4. "Conversar como…", identity and sessions
- **`GET /api/customers`:** `[{id, name, city}]`, the fields the selector shows (customer-selector.md: "no PII on screen beyond name and city"). Never phone or e-mail. A curated 6–8 customers (ids whose orders exercise the traps, e.g. the owners of orders 5 and 7) keeps the list scannable; the CSV is case fixture data.
- **`PUT /api/identity {customer_id | null}`:** validates with `Agent.customer_exists`, stores it in the session and **rotates `sid`** (the design's "a new session id starts below it"). The client never sends identity with a message.
- **Thread isolation bug for a public demo:** `ChannelIdentity.thread_id()` is `web:customer:<id>` with no session (`support/domain/channel_identity.py`). Two evaluators who both pick "Ana" would share one LangGraph thread and read each other's turns. Include the session for identified customers (`{channel}:customer:<id>:<session>`). Side effect: the CLI makes a new uuid per run, so CLI customer memory no longer spans runs; nothing depends on it (unconfirmed for multi-turn evals; check). R8 pseudonymization keeps working on the new id.
- **Anonymous:** default; `sid` from `secrets.token_urlsafe(16)` at login, server-generated only.

**Recommendation:** name + city list, identity in the signed session, `sid` rotated on every switch, and session-scoped customer threads.

## 5. Frontend
- **Scaffold** (https://ui.shadcn.com/docs/installation/vite): `npm create vite@latest frontend -- --template react-ts`; `npm i tailwindcss @tailwindcss/vite`; `src/index.css` = `@import "tailwindcss";`; `@` alias in `tsconfig*.json` and `vite.config.ts`; `npx shadcn@latest init`; `npx shadcn@latest add button card input label select textarea badge avatar` (component-plan.md).
- **Tokens:** `emporio-da-musica.theme.json` is a shadcn `registry:theme` item with OKLCH `cssVars`; apply it into `:root`/`.dark` (token-mapping.md says via `/gsp-brand-apply`, do not hand-paste), plus the hand-written `@theme inline` bridge (token-mapping.md §5).
- **Fonts:** `import "@fontsource-variable/fraunces"` and `"@fontsource-variable/source-sans-3"`. The variable packages register the families as **"Fraunces Variable"** and **"Source Sans 3 Variable"** (verified in the packages' `index.css`), while the theme says "Fraunces"/"Source Sans 3": set `--font-sans`/`--font-display` to the Variable names first. Italic Fraunces (tagline) needs `import "@fontsource-variable/fraunces/wght-italic.css"` (file present in 5.3.0, checked on jsDelivr).
- **SSE from POST:** `EventSource` is GET-only with no body, so use `fetch` + `response.body` + `eventsource-parser` (4.1.3, maintained). `@microsoft/fetch-event-source` has had no release since 2021. Cookie auth is automatic on same origin. No auto-reconnect: a broken stream becomes the design's `error` state ("Manda de novo?"), never a silent resend.
- **No router:** login → warm-up → chat are states of one shell (screen 01 "warm-up is a body state"), so no client routes and no SPA fallback to maintain. `sessionStorage` holds the queued message (screen 02).
- **Hooks** (component-plan.md): `useSession`, `useWarmStatus` (seeded by the login response, 1 s poll), `useChatStream` (honours `delay_ms`), `useQueuedMessage`. No state library.
- **Accessibility musts from the design:** `role="log"` transcript with bubbles appended only when complete; `role="status"` typing indicator outside the log; one persistent `role="status"` region in `<main>` for warm-up announcements; only `failed` is `role="alert"`; `aria-disabled` (not `disabled`) on Send; focus never jumps into the log; `prefers-reduced-motion` drops fade and dot pulse but **not** pacing; targets ≥ 44 px (links ≥ 24 px); reflow at 320 px and the `max-height: 480px` rule; `lang="pt-BR"`; rem units.
- **Client pacing:** for each `bubble`, keep typing on, `await sleep(delay_ms)`, append. Bubbles queue in order even if the stream delivers them at once.

**Recommendation:** the shadcn Vite path with Tailwind v4, theme.json tokens plus the Variable font names, `fetch` + `eventsource-parser`, state-driven screens with no router.

## 6. Same-origin serving
- One FastAPI app serves `/api/*` and, mounted last, `StaticFiles(directory=frontend/dist, html=True)` at `/`. With no client routes, `html=True` (serves `index.html` for `/`) is enough. Missing `dist` in dev must not crash the API: mount only if the directory exists.
- Prefix the API with `/api` (a cosmetic deviation from the spec's `/auth/login`, which keeps static and API paths apart).
- Vite dev: `server.proxy = {"/api": "http://localhost:8000"}`; SSE passes through the Vite proxy (unconfirmed for buffering; verify once).
- Modal: streaming from FastAPI works when the media type is `text/event-stream`, which tells Modal to "return responses immediately" (https://modal.com/docs/guide/streaming-endpoints). Static serving under `@modal.asgi_app` was not checked (phase 6).

**Recommendation:** `/api` routers plus `StaticFiles(html=True)` for `dist`, a Vite proxy in dev, one origin everywhere.

## 7. `make up` and `make e2e`
- **`make up`:** prerequisite check (docker, uv, node ≥ the Vite 8 minimum, unconfirmed) and a printed plan → `check-config` (fails in seconds on a missing key, existing pattern) → `make db` → `make langfuse-up` (mandatory; first pull ≈ 7 min, ≈ 2.3 GB RAM, AGENTS.md) → `npm ci && npm run build` → `uvicorn` serving API and `dist` on one port. One process and one URL, the same shape as Modal. A separate `make dev` runs uvicorn `--reload` and Vite with HMR.
- **`PROVIDER=gemini|openai|anthropic`** already works through `LLM_PROVIDER`. `PROVIDER=local` (Ollama, hardware detection) is new work (§ decisions).
- **e2e runner:** spec §5 says "TS only in React", so use **pytest-playwright** (Python) in `e2e/`, not `@playwright/test`. One pytest fixture starts uvicorn on a free port; the browser hits the built app.
- **Determinism:** `EVAL_FAKE_MODEL=1` already exists in `tests/eval/test_agent_evals.py`. Promote it to one composition-root switch (`EMPORIO_FAKE_MODEL=1` in `bootstrap.build_agent`) that injects a scripted chat model and a fixed classifier; the default `make e2e` runs on it (no key, no GPU, seconds), and `make e2e PROVIDER=gemini` runs the same flow on a real model with looser assertions (bubbles exist, no error). Langfuse stays on in both, as the owner ruled.
- **Flow:** login → warm status ready (`provider_api`/fake) → send → typing → ≥ 1 bubble → metrics summary updates → switch customer → divider; plus wrong password and a queued message during a simulated warm-up.

**Recommendation:** `make up` builds and serves one port after the existing checks; e2e in Python Playwright against a fake model by default.

## 8. Testing under the deadline
- **API:** `TestClient` with a fake `Agent` (the dataclass already takes plain callables) and a fake warm probe. SSE: `with client.stream("POST", "/api/chat", json=...)` then parse `event:`/`data:` lines. Contract tests pin the event names and payload keys plus the `/warm/status` and `/customers` shapes (one test each, not OpenAPI snapshots).
- **Domain:** `pace_bubbles` and thread-id changes as pure unit tests (TDD pairs).
- **Frontend:** Vitest only for pure logic (SSE event reducer, pacing queue, `ceil10`, elapsed formatting, queued-message join/undo). Component tests duplicate the e2e; skip them.
- **CI:** add `npm ci && npm run build && npx vitest run` to `ci.yml`; e2e stays local (needs Docker + Langfuse).

**Recommendation:** TestClient contract tests + pure-function Vitest + a handful of e2e paths; no component test suite.

## 9. Phase 4 backlog
- **R9 (drop unanswered `tool_calls` at trim time): do it in phase 5.** ~10 lines in the agent node, and a public demo turns a 400 into a dead thread for that session. With option (A) a disconnect can no longer cause it, but a container death still can.
- **New eval cases (abuse, "é robô?", complaint, promo format, multi-turn; PR-5 row 11): phase 5**, TOML only, run with the real-provider eval still pending a key.
- **Customer first name in traces (PR-5 row 11, L3.4): phase 6**, as a gate before switching to Langfuse Cloud; it is local-only until then.
- PR-2 rows 8–10 and 15 are closed by §1 and §3 plus a spec "API contracts" section.

**Recommendation:** R9 and the eval cases now; first-name masking as a phase 6 pre-Cloud gate.

## Proposed task breakdown for the plan
1. API skeleton: `api/app.py` factory taking an `Agent`, lifespan via `bootstrap`, session auth (`/api/auth/login|logout|me`), login limiter, `StaticFiles` mount; TestClient tests with a fake Agent.
2. `/api/chat` SSE: `pace_bubbles` in `support/domain/bubbles.py`, invoke-then-emit events, `metrics` with the `action` map, per-thread 409 lock, input limits, chat limiter; contract tests.
3. Identity: `/api/customers` (curated, name + city), `PUT /api/identity` rotating `sid`, session-scoped customer threads in `ChannelIdentity`.
4. Frontend scaffold: Vite + TS + Tailwind v4 + shadcn, theme tokens, Fontsource Variable names, Vite proxy; login screen and a minimal chat (text bubbles, typing, paced append) end to end.
5. `EMPORIO_FAKE_MODEL` switch in `bootstrap`, `make up` (one port), `make dev`, and `make e2e` with one pytest-playwright happy path.
6. Warm-up backend: warm service (mode by provider, single-flight `/health` probe with 303/timeout handling, deadline → failed), `/api/warm`, `/api/warm/status` with `elapsed_seconds`, `expected_seconds`, `reply_p50_seconds`; login returns the status.
7. Warm-up UI: WarmupStatus per mode, persistent StatusRegion, count-up from server time, network error after 3 failed polls, long wait, retry, queued message with undo and `sessionStorage`, ready focus rule.
8. Chat completeness: CustomerSelector + divider, Métricas `<details>` (last reply, session, history), error and partial-error states, "Novas mensagens", reduced motion, 320 px and short-viewport reflow.
9. R9 drop of unanswered `tool_calls` in the agent node (TDD) and the five new eval cases.
10. Hardening: CI front build + Vitest, `.env.example` names, spec "API contracts" section, e2e for wrong password, customer switch and queued message, manual VoiceOver and 320 px zoom pass.

## Decisions to confirm with the owner
1. **Bubble delivery:** invoke-then-emit (recommended: simple, disconnect-safe, matches the design's "bubble 1 at 0 ms after generation") or token streaming so bubble 1 lands ~1–2 s earlier at the cost of a worker thread, preamble filtering and end-of-turn reconciliation?
2. **GPU warm-up stages:** show one honest stage until `/health` answers, or add Modal `get_current_stats()` (undocumented fields) to show "Ligando a GPU" → "Carregando o modelo" as the design draws it?
3. **`make up PROVIDER=local` (Ollama + hardware detection):** build it in phase 5, or move it to phase 6 and ship phase 5 with hosted Gemma and the API providers only (the `local_cpu` UI variant would still be built, fed by config)?
4. **ProductCard and HandoffBubble:** text-only bubbles in phase 5 (recommended; the agent has no handoff tool and a product card needs structured tool output per turn), or derive `kind: "product"` from the turn's tool results now?

## Risks
- **Shared customer threads** across evaluators until §4's thread fix lands; it leaks one tester's turns into another's model context.
- **Cold start (175 s) > Modal's 150 s request limit:** a naive probe sees a 303 or a timeout and reports `failed`.
- **Langfuse is mandatory**, so `make up` and `make e2e` need its 7-minute first pull and ~2.3 GB RAM; a clean-clone evaluator on a small laptop may stall there.
- **TypeScript 7.0** (native compiler) is what `create-vite` pins today; shadcn's Vite guide still tells you to set `baseUrl`, which newer TypeScript deprecates. Use `paths` without `baseUrl`, and fall back to `typescript@~5` if the shadcn CLI or `tsc -b` breaks (compatibility unconfirmed).
- **Font family mismatch** (Variable packages vs theme names) would silently fall back to system fonts.
- **Per-process state** (thread locks, warm state, rate limits) breaks if the Modal API runs more than one container; pin it to one container for the demo or move to Postgres (advisory lock, one-row warm table).
- **Proxy IP on Modal** may make the per-IP login limit global (unconfirmed `X-Forwarded-For`).
- **Deadline:** phase 5 is the largest UI surface; cut order inside the phase is metrics history → "Novas mensagens" pill → long-wait copy, never the warm-up honesty or accessibility basics.

## Owner decisions (2026-11-06)
- Bubbles: run the whole turn, then send bubbles paced with server-computed `delay_ms` (no token streaming).
- GPU warm-up: one honest stage ("Ligando o modelo") with the timer until vLLM `/health` answers; no undocumented Modal stats.
- `make up PROVIDER=local` (Ollama + hardware detection) moves to phase 6; the local-mode warm-up screen is still built in phase 5, driven by config.
- Text-only bubbles in phase 5; product cards later if time allows.
