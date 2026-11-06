# Phase 6: GPU sizing, cold start, deploy and scale — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the evaluator opens one `*.modal.run` URL, logs in and talks to Gemma 4 31B FP8 on a measured GPU. Every number the spec demands is measured, not estimated: the GPU table (cost × latency × evals), the cold-start breakdown with each optimization, the load test, and the cost per conversation.

**Architecture:**
- **GPU app:** `deploy/modal_llm.py` serves vLLM behind `@modal.web_server`. GPU and weights are chosen at deploy time (`EMPORIO_GPU=H100|L40S`, `EMPORIO_WEIGHTS=fp8|bf16`), and each pair is its own Modal app (`emporio-llm-<gpu>-<weights>`), so a measurement never invalidates another. Weights sit on an HF-cache Volume, and compile artifacts on a `vllm-cache` Volume.
- **API app:** `deploy/modal_api.py` returns `emporio.web.create_web_app()` from `@modal.asgi_app()`, pinned to `max_containers=1` because rate limits, locks and warm-up state are per process. The image is built with `uv_sync`, bakes the e5 model and carries `data/`, `backend/migrations` and `frontend/dist` in the repo layout `paths.REPO_ROOT` expects. It finds the vLLM URL at container start with `modal.Function.from_name(...).get_web_url()`, so no URL (which contains the workspace name) is ever written in the repo.
- **Data and tracing:** Postgres + pgvector on Railway, reached over its TLS public proxy. Migrations and ingestion run once from a Modal function in the same image, so ingestion uses the same baked e5 files as queries. Langfuse Cloud EU, only after customer names are masked in spans.
- **Load:** Locust `HttpUser` against a throwaway fake-model API app (`emporio-api-loadtest`) with limits raised by one env multiplier. A small real-model run against the demo app happens only if time is left.
- **Local:** `make up PROVIDER=local` runs Ollama (native on Apple Silicon, Docker CPU or Docker NVIDIA), driven by a tested size/route chooser.

**Tech stack:** modal 1.6.3 (`@modal.web_server`, `@modal.asgi_app`, `@modal.concurrent`, `Image.uv_sync`, `run_function`), vLLM 0.33.0 (or the newest that builds; ≥ 0.19.1), `RedHatAI/gemma-4-31B-it-FP8-dynamic`, langfuse 5.2 (Cloud EU), fastembed 0.9.1, locust 2.47.0, Ollama v0.40.15.

**Spec:** `docs/superpowers/specs/2026-11-05-emporio-agent-design.md` §5 (GPU sizing, cold start, deploy), §7.2.2–7.2.4 (deferrals to phase 6), §7.3.1, §7.5, §7.9 (phase 6 row and cut order), §7.14. **Research + owner decisions (binding):** `docs/research/fase-6.md`, including "Owner decisions" (2026-11-06). **Backlog:** `.superpowers/reviews/2026-11-06-pr-6/verdict.md` row 21 (client IP behind Modal), the spec's phase 6 gates (first-name masking before Langfuse Cloud, a stable `LANGFUSE_SALT`, the baked e5 model, the Gemini price, `WARM_READY_TTL_SECONDS` tied to the scaledown), and the limits for e2e and load testing raised through env. Rows 1 and 13 are already closed in code (overall chat window; `docs_url=None`).

## Global Constraints
- **Branch and commits:** branch `feat/deploy` (already checked out; do not switch). TDD pairs are `test(<scope>): … (red)` then `feat(<scope>): …`, with scopes `deploy`, `support`, `api`, `config`, `loadtest`, `web`, `e2e`, `evals` and `docs`. Scaffolding goes in `chore`/`build` commits, never in a red commit. Subject ≤ 72 chars, imperative. Every commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Run `export PATH="$PWD/backend/.venv/bin:$PATH"` before committing. Never `--no-verify`, never amend, never force-push, never `# noqa`. Merges are merge commits.
- **Gates:**
  - `make check` is green on every non-red commit, offline, with no keys, no DB and no Langfuse server.
  - `make check-web` is green on every commit that touches `frontend/`.
  - `make test-pg` and `make e2e` are green before the PR.
  - `deploy/` and `loadtest/` join the `make lint` ruff line (like `e2e`). They have no unit tests of their own beyond Task 4's constants test; the deploy and the measurements are their test.
- **Owner-only actions** (an agent never does these, and never prints, copies, echoes or commits a secret value; agents reference variable and secret names only):
  - Modal auth, the Modal dashboard (credit check, budget alert) and creating Modal secrets with real values.
  - Creating the Railway Postgres and putting its URL in `.env`.
  - The Langfuse Cloud EU project and its keys.
  - Provider keys and demo credentials in `.env`.
  - Values reach `.env` through the owner's editor. The `!` commands below read them from `.env`, so no value ever appears on a command line or in the transcript.
- **Paid steps are gated:** a step marked **[ASK $]** costs Modal money (a GPU run or any deploy). The controller stops, tells the owner the expected cost, and runs it only after the owner says yes. After every GPU measurement the controller runs `modal container stop` on the GPU containers, so the 10-min idle window is not billed. The research's estimated total for this phase is about $10–12 of the $30 monthly credit.
- **Secrets:** `.env` (git-ignored) and the Modal secrets `emporio-vllm` (`VLLM_API_KEY`), `emporio-hf` (`HF_TOKEN`, only if a repo is gated), `emporio-db` (`DATABASE_URL`), `emporio-langfuse` (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`, `LANGFUSE_SALT`) and `emporio-web` (`DEMO_EMAIL`, `DEMO_PASSWORD`, `SESSION_SECRET`). `emporio-langfuse` is created once and never recreated: a new salt changes every pseudonym. `.env.example` gains names only: `RAILWAY_DATABASE_URL`, `CLOUD_LANGFUSE_PUBLIC_KEY`, `CLOUD_LANGFUSE_SECRET_KEY`, `RATE_LIMIT_MULTIPLIER`, `GPU_USD_PER_HOUR`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`.
- **Repo hygiene:** no personal names, other projects, workspace names, `*.modal.run` URLs or local absolute paths in any committed file. English code and docs; pt-BR `README.md` and UI copy.
- **Langfuse stays mandatory**, including on the load-test app. Never cut.
- **Owner decisions (2026-11-06, binding):**
  1. Measure L40S and H100 with `RedHatAI/gemma-4-31B-it-FP8-dynamic`; the default is H100 + FP8. If FP8 scores lower than BF16 on the evals, fall back to BF16 on H100 and document it.
  2. GPU `scaledown_window` 600 s; `WARM_READY_TTL_SECONDS` 540.
  3. `PROVIDER=local` is the lean version: native macOS, Docker CPU and Docker NVIDIA detection, the three warnings, a Modelfile with `num_ctx 16384`, and one eval run on the owner's Mac.
  4. The GPU memory snapshot is time-boxed to 90 min at the end and documented either way. Locust runs against a fake-model app at 100–300 users. A 10–20 user real-model run happens only if time is left.
- **Cut order (spec §7.9), applied from the last task backwards:** first the real-model load test (Task 11), then metrics panel polish (Task 10), then the GPU snapshot (Task 9). Never cut the deploy, Langfuse or the measured numbers.
- **Time:** Tasks 1–8 are about 10.5 h of mostly waiting on GPUs; 9–11 add about 3 h. That is more than one day, so the cut order is expected to bite.

### Owner prerequisites (in order; `ENV` means the prefix `set -a; . ./.env; set +a;`)
1. **Before Task 1: Modal auth and credit.** `! modal token new`. Then, in the dashboard, confirm this month's $30 credit and set a budget alert.
2. **Before Task 1: vLLM key and HF token.**
   - `! grep -q '^VLLM_API_KEY=' .env || printf 'VLLM_API_KEY=%s\n' "$(openssl rand -hex 24)" >> .env`
   - `! modal secret list` shows the existing secrets. If `emporio-vllm` is missing: `! ENV modal secret create emporio-vllm VLLM_API_KEY="$VLLM_API_KEY"`.
   - If a weights repo is gated (Task 1 step 2 says so), put `HF_TOKEN` in `.env` with the editor, then `! ENV modal secret create emporio-hf HF_TOKEN="$HF_TOKEN"`.
3. **Before Task 4: Railway.** Create the Postgres (pgvector template) in the existing Railway project, region US East, with app sleeping off. Copy the public proxy URL into `.env` as `RAILWAY_DATABASE_URL=…?sslmode=require` (editor). Then `! ENV modal secret create emporio-db DATABASE_URL="$RAILWAY_DATABASE_URL"`.
4. **Before Task 4: Langfuse Cloud EU.** Create the project and put `CLOUD_LANGFUSE_PUBLIC_KEY` and `CLOUD_LANGFUSE_SECRET_KEY` in `.env` (editor). Then, once and never again: `! ENV modal secret create emporio-langfuse LANGFUSE_PUBLIC_KEY="$CLOUD_LANGFUSE_PUBLIC_KEY" LANGFUSE_SECRET_KEY="$CLOUD_LANGFUSE_SECRET_KEY" LANGFUSE_BASE_URL=https://cloud.langfuse.com LANGFUSE_SALT="$(openssl rand -hex 16)"`.
5. **Before Task 4: demo credentials.** Set `DEMO_EMAIL` and a strong `DEMO_PASSWORD` in `.env` (editor). Then `! ENV modal secret create emporio-web DEMO_EMAIL="$DEMO_EMAIL" DEMO_PASSWORD="$DEMO_PASSWORD" SESSION_SECRET="$(openssl rand -hex 32)"`.
6. **Optional, any time:** `GEMINI_API_KEY` (or another provider key) in `.env`, for the comparison eval rows still pending since phase 5 (R3).
7. **Before Task 8:** install Ollama on the Mac (https://ollama.com/download) and agree to a download of about 20 GB.

## Review Focus
1. **A customer's name reaching Langfuse Cloud in any casing or inside a sentence** ("aqui é a ana carolina", "LUCAS"). Expected: it is masked in every span attribute except our pseudonymous ids, and a word that only contains a name ("banana", "Lucastro") is kept. Tests: Task 3 `test_mask_redacts_customer_names_any_case` and `test_mask_keeps_words_that_contain_a_name`.
2. **Raised rate limits leaking onto the real GPU deployment.** Expected: `RATE_LIMIT_MULTIPLIER > 1` without `EMPORIO_FAKE_MODEL=1` fails at boot, so a paid GPU app can never run without the cost guard. Test: Task 5 `test_rate_multiplier_requires_fake_model`.
3. **A spoofed `X-Forwarded-For` behind the Modal proxy** (if Task 5 finds that `request.client.host` is the proxy). Expected: a client that sends its own header still shares one per-IP bucket, so it cannot get past 5 logins per minute. Test: Task 5 `test_spoofed_forwarded_for_does_not_bypass_login_limit`.
4. **The warm `ready` outliving the GPU.** If the GPU scales down at 600 s while the API still says `ready`, the evaluator's first message gets a cold GPU and no warm-up screen. Expected: the TTL stays under the scaledown window. Test: Task 4 `test_ready_ttl_is_under_gpu_scaledown`.
5. **A Gemma turn without a GPU price** (local dev against vLLM, or a price missing for a GPU type). Expected: `cost_brl` is `null` with "Custo de GPU ainda não medido", never a zero cost. Test: Task 7 `test_gemma_cost_null_without_gpu_price`.

---

### Task 1: vLLM Modal app in the repo

**Files:**
- Create: `deploy/modal_llm.py`, `deploy/cold_start.py`
- Modify: `backend/pyproject.toml` (dev group `modal>=1.6.3`; `uv lock`), Makefile (`lint` adds `deploy loadtest`; new target `deploy-llm`), `.env.example`

**Interfaces:**
- Produces, in `deploy/modal_llm.py`:
  - `GPUS = ("H100", "L40S")` and `WEIGHTS = {"fp8": ("RedHatAI/gemma-4-31B-it-FP8-dynamic", "<sha>"), "bf16": ("google/gemma-4-31B-it", "<sha>")}`. Pin each revision to the HF commit sha read on the day.
  - `GPU_SCALEDOWN_SECONDS = 600`.
  - The app name `f"emporio-llm-{gpu.lower()}-{weights}"`, read from `EMPORIO_GPU` (default `H100`) and `EMPORIO_WEIGHTS` (default `fp8`). Both are validated, and both are also written into the image `.env()`, so the container's re-import sees the deploy-time values.
  - `download` (CPU function) runs `snapshot_download(repo, revision=sha)` into the HF-cache Volume. Reuse the spike's HF-cache Volume if `modal volume list` shows one; otherwise create `huggingface-cache`. The `vllm-cache` Volume is mounted at `/root/.cache/vllm`.
  - `serve`: `gpu=GPU`, `scaledown_window=GPU_SCALEDOWN_SECONDS`, `max_containers=1` (a cost guard), secrets `emporio-vllm` (+ `emporio-hf` if gated), `@modal.concurrent(max_inputs=32)` and `@modal.web_server(port=8000, startup_timeout=600)`.
  - It spawns `vllm serve <repo> --revision <sha> --served-model-name google/gemma-4-31B-it --max-model-len 16384 --enable-prefix-caching --kv-cache-dtype fp8 --gpu-memory-utilization 0.92 --enable-auto-tool-choice --tool-call-parser gemma4 --api-key $VLLM_API_KEY --host 0.0.0.0 --port 8000`. The served name keeps `Settings.gemma_model` unchanged. No `--reasoning-parser`: we run without thinking.
  - A daemon thread prefixes each vLLM stdout line with `[boot +<s>s]`, counted from container start. The cold-start breakdown is read off those lines (weight load, `torch.compile`, graph capture, server up).
- Produces `deploy/cold_start.py --app <name>`:
  - stops the app's running containers (`modal container list --json`, `modal container stop`);
  - resolves the URL with `modal.Function.from_name(app, "serve").get_web_url()`;
  - polls `GET /health` every 2 s with the bearer from env `VLLM_API_KEY` (`follow_redirects=False`, 10 s timeout);
  - prints `cold_start_s=<n>`, then times one `/v1/chat/completions` "Oi" and prints `first_reply_s=<n>`. It never prints the key or the URL.
- Makefile `deploy-llm`: `cd backend && EMPORIO_GPU=$(GPU) EMPORIO_WEIGHTS=$(WEIGHTS) uv run modal deploy ../deploy/modal_llm.py`, with defaults `GPU=H100` and `WEIGHTS=fp8`.

- [ ] **Step 1:** write `deploy/modal_llm.py`, `deploy/cold_start.py`, the dep, the Makefile lines and the names in `.env.example`. Follow the image recipe of https://modal.com/docs/examples/vllm_inference, with vLLM pinned. `make check` green. Commit `build(deploy): add the vLLM Modal app with FP8 weights and boot timing`.
- [ ] **Step 2:** check whether the two repos are gated (`curl -s https://huggingface.co/api/models/<repo> | jq .gated`). If either is, owner prerequisite 2's `emporio-hf` is needed before the download.
- [ ] **Step 3 [ASK $ ≈ $0.05, CPU]:** `cd backend && uv run modal run ../deploy/modal_llm.py::download` with `EMPORIO_WEIGHTS=fp8`. Expected: the run ends with the snapshot path on the Volume.
- [ ] **Step 4 [ASK $ ≈ $0.30, first H100 boot]:** `make deploy-llm`, then `cd backend && uv run python ../deploy/cold_start.py --app emporio-llm-h100-fp8`. Expected: `cold_start_s` is printed, and the `[boot +…]` lines in `modal app logs emporio-llm-h100-fp8` show the stages.
  - If vLLM fails on the tool parser or the chat template, add the recipe's `--chat-template examples/tool_chat_template_gemma4.jinja` and record that in the report.
  - Stop the containers.
- [ ] **Step 5:** the controller writes the non-secret `VLLM_BASE_URL=<web url>/v1` into the git-ignored `.env`, replacing any old line, and does not paste it anywhere else.

### Task 2: measure GPU × weights (cold start, evals, latency)

**Files:**
- Create: `docs/scaling-and-cost.md` (English: the GPU table, the cold-start table, and the methods)
- Modify: `backend/src/emporio/config.py` (`warm_expected_seconds_gpu` default = the measured H100 FP8 warm cold start, rounded up to 10 s), `backend/evals/reports/gemma-*.md` (force-added)

**Interfaces:**
- Consumes: Task 1 `make deploy-llm GPU=… WEIGHTS=…`, `deploy/cold_start.py`, `VLLM_BASE_URL` in `.env`.
- Produces: in `docs/scaling-and-cost.md`, the table `| GPU | weights | $/h | cold start (cache cold / warm) | p50 / p95 ms | evals pass | AI tells | tokens/s |` and the cold-start table `| technique | cold start s | delta |`. The baseline row is the spike's 175 s on H200 BF16.

For each config, the run is the same:
- `cold_start.py` twice: the first boot has a cold compile cache, the second a warm one;
- `make evals PROVIDER=gemma`, then `mv backend/evals/reports/gemma.md backend/evals/reports/gemma-<gpu>-<weights>.md`;
- read p50/p95 from the report, and tokens/s from vLLM's throughput log line;
- stop the containers.

- [ ] **Step 1 [ASK $ ≈ $1.30]:** H100 FP8. Gate per spec §10: ≥ 90% pass and 0 AI tells.
- [ ] **Step 2 [ASK $ ≈ $0.80]:** `make deploy-llm GPU=L40S`, then the same run. Expected (research estimate): a median above 3 s. Record it either way.
- [ ] **Step 3 [ASK $ ≈ $1.50 incl. a 62 GB download]:** the BF16 baseline on H100 (`WEIGHTS=bf16`: `download`, `deploy-llm`, the run). It is needed because owner decision 1 compares FP8 against BF16.
  - If FP8 passes fewer cases than BF16 on H100, the default becomes `bf16` (Task 4 deploys that app), and the regression is documented.
  - If the controller is short of time, ask the owner whether to skip this step and keep FP8 when it meets the gate.
- [ ] **Step 4 (optional, ≤ 20 min) [ASK $ ≈ $0.30]:** one H100 FP8 boot with `--compilation-config '{"cudagraph_capture_sizes": [1, 2, 4, 8, 16]}'`. Keep it only if the cold start drops with no p50 loss.
- [ ] **Step 5:** write the tables into `docs/scaling-and-cost.md`, set `warm_expected_seconds_gpu` to the measured value, then run `make check`. `git add -f` the eval reports. Commit `docs(deploy): measured GPU sizing and cold-start breakdown`.

### Task 3: Langfuse Cloud gate — mask customer names in spans

**Files:**
- Modify: `backend/src/emporio/support/infrastructure/tracing.py`, `backend/src/emporio/orders/infrastructure/csv_order_repository.py` (`CsvCustomerRepository.names() -> tuple[str, ...]`), `backend/src/emporio/bootstrap.py`
- Test: `backend/tests/unit/support/test_tracing.py` (extend)

**Interfaces:**
- `name_pattern(names: Iterable[str]) -> re.Pattern[str] | None`:
  - the alternatives are each full name and its first token, dropping tokens shorter than 3 characters, longest first;
  - bounded by `(?<!\w)` and `(?!\w)`, with `re.IGNORECASE`;
  - `None` when there are no names.
- `redact(text: str, names: re.Pattern[str] | None = None) -> str`: the existing PII masking, then names → `REDACTED`.
- `make_mask(names: re.Pattern[str] | None) -> Callable[..., MaskOtelSpansResult]` replaces the module-level `mask_otel_spans`. It keeps the `_IDENTIFIER_KEYS` skip.
- `make_langfuse(settings: Settings, customer_names: Sequence[str] = ()) -> Langfuse`; `build_agent` passes `customers.names()`.
- Mark the name pattern `# ponytail: masks every CSV customer name, so a name that is also a common word is over-redacted; switch to per-turn names if traces lose meaning.`

- [ ] **Step 1: failing tests:**
  - `test_mask_redacts_customer_names_any_case`: with names `("Lucas Mendes da Silva", "Ana Carolina Ferreira")`, the input `"oi, aqui é a ana carolina ferreira e o LUCAS"` contains none of `ana`, `carolina`, `lucas` (casefolded) after masking;
  - `test_mask_keeps_words_that_contain_a_name`: `"banana"` and `"Lucastro"` are unchanged;
  - `test_mask_never_rewrites_identifier_keys`: a `session.id` holding `cust-…` and a name stays as it was;
  - `test_existing_pii_masking_unchanged_with_names`: `test_mask_redacts_email_phone_cpf` passes through `make_mask(name_pattern(...))`.
- [ ] **Step 2:** red commit `test(support): mask customer names in trace spans (red)`. Implement, `make check`, then `feat(support): mask customer names before Langfuse Cloud`.

### Task 4: API on Modal with Railway and Langfuse Cloud

**Files:**
- Create: `deploy/modal_api.py`, `backend/tests/unit/test_deploy_config.py`
- Modify: Makefile (`deploy-api: web-build`), `AGENTS.md` (deploy commands, the secret names, "never recreate `emporio-langfuse`")

**Interfaces:**
- Consumes: Task 1 app names and `GPU_SCALEDOWN_SECONDS`; Task 2's chosen default `<gpu>-<weights>`; Task 3 masking; owner prerequisites 3–5.
- `deploy/modal_api.py`:
  - `WARM_READY_TTL_SECONDS = 540` and `GPU_PRICES = {"H100": "3.95", "L40S": "1.95"}` (USD/h, modal.com/pricing 2026-11-06).
  - `EMPORIO_LLM_APP` (default `emporio-llm-h100-fp8`, or `-bf16` per Task 2) and `EMPORIO_LOADTEST` (unset or `1`) are read at deploy time and written into the image `.env()`.
  - **Image:** `debian_slim(python_version="3.12")` → `uv_sync(uv_project_dir="backend", frozen=True)`, with no dev group and the project itself not installed. Then `add_local_dir` for `backend/src`, `backend/migrations`, `data` and `frontend/dist`, under `/app/...` (so `REPO_ROOT` resolves to `/app`), and `PYTHONPATH=/app/backend/src`.
  - **e5:** `.env({"FASTEMBED_CACHE_PATH": "/models/fastembed"})` → `run_function(bake_e5)`, which builds `E5Embedder()` and embeds one query. Then `.env({"HF_HUB_OFFLINE": "1"})`, so a runtime download fails loudly. If fastembed 0.9.1 does not read `FASTEMBED_CACHE_PATH`, add a `Settings.embeddings_cache_dir` passed to `E5Embedder(cache_dir=…)` instead.
  - **Env:** `WARM_READY_TTL_SECONDS`, `GPU_USD_PER_HOUR=GPU_PRICES[gpu of EMPORIO_LLM_APP]`, `LLM_PROVIDER=gemma`.
  - **`web`:** secrets `emporio-db`, `emporio-langfuse`, `emporio-web` and `emporio-vllm`; `max_containers=1`, `scaledown_window=300`, `@modal.concurrent(max_inputs=100)`, `@modal.asgi_app()`. Its body sets `VLLM_BASE_URL` from `modal.Function.from_name(EMPORIO_LLM_APP, "serve").get_web_url() + "/v1"`, then returns `create_web_app()`. The app name is `emporio-api`.
  - **Load-test variant:** with `EMPORIO_LOADTEST=1`, the app is `emporio-api-loadtest`. It sets `EMPORIO_FAKE_MODEL=1` and `RATE_LIMIT_MULTIPLIER=100`, does not use `emporio-vllm` and skips the URL lookup.
  - **`ingest`:** a CPU function on the same image with `emporio-db`. It runs `python -m emporio.migrate` then `python -m emporio.ingest`.
- `test_deploy_config.py` reads the constants with `ast` (no `modal` import):
  - `test_ready_ttl_is_under_gpu_scaledown`: `0 < scaledown - ttl <= 120`;
  - `test_gpu_prices_cover_every_gpu`: `GPU_PRICES` keys == `set(GPUS)`.

- [ ] **Step 1:** failing `test_deploy_config.py` → red commit `test(deploy): tie the warm TTL to the GPU scaledown (red)`. Write `deploy/modal_api.py` and the Makefile target, `make check`, then `feat(deploy): add the API Modal app with baked e5 and Railway`.
- [ ] **Step 2 [ASK $ ≈ $0.05, CPU]:** `cd backend && uv run modal run ../deploy/modal_api.py::ingest`. Expected: migrations applied (001 creates `vector`, which proves pgvector) and ingestion counts printed (25 policy chunks plus the product embeddings).
- [ ] **Step 3 [ASK $, deploy, CPU only while idle]:** `make deploy-api`. Smoke as the owner would:
  - open the URL, log in, and watch the warm-up go from "Ligando o modelo" to ready;
  - send "Oi, vocês têm violão Takamine?" as customer 14, and get a reply in bubbles;
  - open Métricas.
  - Then confirm on Langfuse Cloud that the trace exists, its session is `web:cust-…:…`, and no name, e-mail or phone appears in any span.
  - If the trace is missing after container exit, add a `@modal.exit` hook that calls `shutdown_tracing()`.
  - Stop the GPU containers afterwards.
- [ ] **Step 4:** record in the report the boot log lines that prove e5 loaded from `/models/fastembed` with no download, and the client-IP probe. For the probe, an ephemeral `modal serve` of a scratch app (in the scratchpad, not committed) echoes `request.client.host` and `X-Forwarded-For` for a request that sends a fake `X-Forwarded-For: 1.2.3.4`. Write down whether `client.host` is the caller and where Modal puts the real hop. Commit the `AGENTS.md` update as `docs(agents): deploy commands and Modal secrets`.

### Task 5: proxy-aware login limit and a load-test multiplier

**Files:**
- Modify: `backend/src/emporio/config.py`, `backend/src/emporio/api/{auth,chat,app}.py`, `backend/src/emporio/api/guards.py` (`client_ip`, branch (b) only), Makefile (`E2E_FAKE` adds `RATE_LIMIT_MULTIPLIER=10`)
- Test: `backend/tests/unit/test_config.py`, `backend/tests/unit/api/test_auth.py`, `backend/tests/unit/api/test_chat.py`

**Interfaces:**
- `Settings.rate_limit_multiplier: int = Field(1, ge=1)`, from env `RATE_LIMIT_MULTIPLIER`. `require_web_settings` adds the problem `"RATE_LIMIT_MULTIPLIER > 1 needs EMPORIO_FAKE_MODEL=1"` when it is above 1 and the fake model is off.
- `build_chat_router(agent: ChatAgent, settings: Settings)`. Login (5 per IP and 30 overall per 60 s) and chat (20 per `sid` and 200 overall per 600 s) multiply their limits by it. The identity-switch limit is unchanged.
- **Branch (a):** Task 4 found `client.host` is the caller. No code; spec §5 records "confirmed on Modal".
- **Branch (b):** it is a proxy, and Modal appends the real hop to `X-Forwarded-For`.
  - Add `client_ip(request: Request, trust_forwarded: bool) -> str`, which takes the **last** `X-Forwarded-For` entry when trusted, else `client.host`, else `"unknown"`.
  - Add `Settings.trust_proxy_headers: bool = False`, from env `TRUST_PROXY_HEADERS`; `deploy/modal_api.py` sets it to true.

- [ ] **Step 1: failing tests:**
  - `test_rate_multiplier_requires_fake_model`;
  - `test_login_limit_scales_with_multiplier` (multiplier 2 → the 11th login per IP within a minute is 429, the 10th is not);
  - `test_chat_overall_limit_scales_with_multiplier`;
  - branch (b) only: `test_spoofed_forwarded_for_does_not_bypass_login_limit` (six logins, each with a different client-sent first XFF entry and the same last hop → the 6th is 429) and `test_forwarded_ignored_unless_trusted`.
- [ ] **Step 2:** red commit `test(api): env-scaled rate limits (red)`. Implement, `make check`, `make e2e`, then `feat(api): scale rate limits for fake-model load tests`.
- [ ] **Step 3 [ASK $, redeploy]:** branch (b) only: `make deploy-api`, then log in once from a browser to confirm.

### Task 6: fake-model load test

**Files:**
- Create: `loadtest/locustfile.py`
- Modify: `backend/pyproject.toml` (group `load = ["locust>=2.47.0"]`; `uv lock`), Makefile (`loadtest`: `cd backend && uv run --group load locust -f ../loadtest/locustfile.py --headless $(ARGS)`), `docs/scaling-and-cost.md`

**Interfaces:**
- `class Shopper(HttpUser)`, with `wait_time = between(3, 8)`.
  - `on_start`: `POST /api/auth/login` with env `DEMO_EMAIL`/`DEMO_PASSWORD`, then `PUT /api/identity` with a random demo id from `GET /api/customers`.
  - task: `POST /api/chat` with one of five pt-BR messages, using `catch_response=True`. Success means the body has `event: done`; an `event: error` or a missing `done` is a failure named after which one it was.
- Use plain `HttpUser`, not `FastHttpUser`: the reported time must include the whole SSE body.

- [ ] **Step 1:** write the locustfile, the group and the target. Commit `build(loadtest): add the Locust shopper for SSE turns`.
- [ ] **Step 2 [ASK $ ≈ $0.10, CPU deploy]:** `EMPORIO_LOADTEST=1 make deploy-api`.
  - Size the run: count the observations of one fake turn on Langfuse Cloud (a Langfuse SDK `api.trace.get` call that prints only the count). Pick users × turns so the run stays ≤ 20k of the 50k monthly units.
- [ ] **Step 3:** run `make loadtest ARGS="--host <loadtest url> -u 50 -r 10 -t 2m --csv <scratchpad>/fake-50"`, then the sized 100–300 user run (`-r 20 -t 3m`). Record p50/p95/p99, failures by type and requests/s.
  - Identify the bottleneck with evidence: Modal container CPU, the AnyIO thread pool (40), the DB pool (4), or Railway round trips.
- [ ] **Step 4:** `modal app stop emporio-api-loadtest`. Add the numbers and the bottleneck to `docs/scaling-and-cost.md`. Commit `docs(loadtest): fake-model load test results and bottleneck`.

### Task 7: cost — GPU-seconds upper bound and the Gemini price

**Files:**
- Modify: `backend/src/emporio/config.py`, `backend/src/emporio/support/infrastructure/agent/runner.py`, `backend/src/emporio/api/chat.py`, `docs/scaling-and-cost.md`
- Test: `backend/tests/unit/support/test_handle_message.py` (or the runner's cost test beside it), `backend/tests/unit/api/test_chat.py`, `backend/tests/unit/test_config.py`

**Interfaces:**
- `Settings.prices["gemini-3.8-flash"] = (Decimal("0.75"), Decimal("3.75"), Decimal("0.075"))`, with the comment `# list price until 2026-12-31; 1.50 / 7.50 / 0.15 from 2027-01-01`.
- `Settings.gpu_usd_per_hour: Decimal | None = None`, from env `GPU_USD_PER_HOUR`.
- In the runner's cost path, when the model has no list price, the provider is gemma and `gpu_usd_per_hour` is set:
  `cost_brl = gpu_usd_per_hour × (ms_guard + ms_llm) / 3_600_000 × usd_brl`.
  It is an upper bound at concurrency 1. Without the price it stays `None`.
- `chat.py`: `GPU_UPPER_BOUND = "Teto pelo tempo de GPU desta resposta"`. `_cost_basis` returns it for gemma with a cost. `GPU_UNMEASURED` stays for gemma without one.

- [ ] **Step 1: failing tests:**
  - `test_gemini_turn_is_priced`;
  - `test_gemma_turn_cost_is_gpu_seconds_upper_bound` (`3.95` USD/h, ms_guard 400 + ms_llm 1600, usd_brl 5.50 → `Decimal("3.95") * 2 / 3600 * Decimal("5.50")`; the metrics payload says `"0.0121"` and `GPU_UPPER_BOUND`);
  - `test_gemma_cost_null_without_gpu_price`.
- [ ] **Step 2:** red commit `test(support): GPU-seconds cost and Gemini price (red)`. Implement, `make check`, then `feat(support): price Gemma turns by GPU seconds`.
- [ ] **Step 3:** draft in `docs/scaling-and-cost.md`:
  - cost per conversation (GPU upper bound measured from Task 2's tokens and latency, and Gemini/Haiku/Luna list prices);
  - the 1k/10k/100k projections;
  - store-hours vs 24/7 `min_containers` costs;
  - the honest conclusion from research §5.

  Use the research figures, labelled as estimates where not measured. Commit `docs(deploy): cost per conversation and projections`.
- [ ] **Step 4 [ASK $, redeploy]:** `make deploy-api`, so the demo panel shows the GPU-bound cost.

### Task 8: `make up PROVIDER=local` (lean)

**Files:**
- Create: `backend/src/emporio/local_model.py`, `backend/tests/unit/test_local_model.py`
- Modify:
  - `config.py` (`Provider.LOCAL`; `ollama_base_url: str = "http://localhost:11434/v1"`, `ollama_model: str = "emporio-gemma"`; no required variables);
  - `support/infrastructure/llm/factory.py` (LOCAL → the OpenAI-compatible path with `base_url=ollama_base_url` and `api_key="ollama"`);
  - `bootstrap.py` (`build_warmup`: LOCAL → `ProbeWarmup(ollama_load_probe(...), WarmMode.LOCAL_CPU, settings.warm_expected_seconds_local, reply_p50, stage=WarmStage.MODEL_LOADING)`);
  - `support/infrastructure/warmup.py` (`ollama_load_probe`);
  - `api/chat.py` (`LOCAL = "Rodando na sua máquina, sem custo por uso"`);
  - `cli.py` (`emporio local-model`);
  - `docker-compose.yml` (profiles `ollama` and `ollama-nvidia`, image `ollama/ollama:0.40.15`, port 11434, a volume);
  - Makefile (`up` depends on `local-model` when `PROVIDER=local`);
  - `README.md` (pt-BR: the hardware × expected time table, and "para respostas em ~2 s, use a versão hospedada");
  - `AGENTS.md`.
- Test: `backend/tests/unit/test_local_model.py`, `backend/tests/unit/support/test_warmup.py`, `backend/tests/unit/test_config.py`

**Interfaces:**
- `LocalPlan(route: Literal["native", "docker-nvidia", "docker-cpu"], tag: str, download_gb: int, min_ram_gb: int, seconds_per_reply: str)`, a frozen dataclass.
- `choose_local_model(system: str, machine: str, nvidia: bool, mem_gib: int) -> LocalPlan`:
  - `Darwin`/`arm64` → `native`, otherwise NVIDIA → `docker-nvidia`, otherwise `docker-cpu`;
  - `gemma4:31b` with NVIDIA or a Mac with ≥ 32 GiB; `gemma4:12b` at ≥ 16 GiB; else `gemma4:e4b`.
  - `seconds_per_reply` is the research §6 estimate string.
- `emporio local-model` detects the machine (`platform`, `nvidia-smi` plus `docker info` listing `nvidia`, memory from `sysctl hw.memsize` or `/proc/meminfo`). It prints the plan and warning 1 (download size, memory, expected time per reply), then runs:
  - `ollama pull <tag>`;
  - writes a temporary Modelfile `FROM <tag>` + `PARAMETER num_ctx 16384`;
  - `ollama create emporio-gemma -f <file>`.
  - On native it fails with the install link if `ollama` is not on PATH. In Docker it runs the same steps through `docker compose exec`.
- `ollama_load_probe(base_url: str, model: str, timeout: float = 600) -> Callable[[], bool]`: `POST {root}/api/generate {"model", "prompt": "", "keep_alive": "30m"}`; true on 200.

- [ ] **Step 1: failing tests:**
  - `test_mac_32gb_gets_31b_native`;
  - `test_mac_16gb_gets_12b`;
  - `test_linux_nvidia_gets_docker_gpu_31b`;
  - `test_small_cpu_box_gets_e4b`;
  - `test_local_provider_needs_no_key`;
  - `test_ollama_probe_true_only_on_200` (`httpx.MockTransport`);
  - `test_local_turn_cost_basis`.
- [ ] **Step 2:** red commit `test(config): local Ollama provider and model chooser (red)`. Implement, `make check`, then `feat(support): run Gemma locally through Ollama`.
- [ ] **Step 3 (owner prerequisite 7; about 20 GB download):** `make up PROVIDER=local`. Confirm the terminal warning, the `local_cpu` warm-up screen with its notice, and one reply. Then run `make evals PROVIDER=local` and `mv` the report to `local-<tag>.md` (force-added). Add the row to the README table with the machine it was measured on; rows for other hardware are marked "estimativa". Commit `docs(readme): local Ollama mode and measured row`.

### Task 9 (cut 3, time box 90 min): GPU memory snapshot

**Files:**
- Modify: `deploy/modal_llm.py` (`EMPORIO_SNAPSHOT=1` → app `emporio-llm-<gpu>-<weights>-snap`), `docs/scaling-and-cost.md`

**Interfaces:**
- The snapshot variant is a `@app.cls(enable_memory_snapshot=True, experimental_options={"enable_gpu_snapshot": True})` per https://modal.com/docs/examples/vllm_snapshot:
  - `@modal.enter(snap=True)` starts vLLM with `--enable-sleep-mode`, plus `VLLM_SERVER_DEV_MODE=1` and `TORCHINDUCTOR_COMPILE_THREADS=1`. It sends three warm-up chats, then `POST /sleep?level=1`.
  - `@modal.enter(snap=False)` sends `POST /wake_up` and waits for `/health`.
  - `@modal.web_server` is on a method.
  - Keep `--max-num-seqs` at the vLLM default, not the example's 2.

- [ ] **Step 1 [ASK $ ≈ $3–4: 5 H100 boots]:** deploy the snap app and run `cold_start.py` 5 times.
  - Record each restore time. The research expects it to settle after fewer than 5 boots.
  - Confirm that a reply right after restore is correct (asleep `/health` is 200, so check a real completion).
- [ ] **Step 2:** if the settled restore beats Task 2's warm-cache cold start, redeploy the API with `EMPORIO_LLM_APP=…-snap` **[ASK $]** and set `warm_expected_seconds_gpu` to it. Otherwise keep the plain app. Either way, write the result honestly in `docs/scaling-and-cost.md` against the 30 s target. Commit `docs(deploy): GPU memory snapshot result`. Stop the time box at 90 min, whatever the state.

### Task 10 (cut 2): metrics panel polish

**Files:**
- Modify: `frontend/src/chat/MetricsDetails.tsx` (`grid-cols-[auto_minmax(0,1fr)]` and `[overflow-wrap:anywhere]` on `dd`; verdict PR-6 row 19)
- Test: `e2e/test_demo_flow.py`

- [ ] **Step 1:** e2e `test_metrics_panel_fits_320px`: viewport 320 × 640, one turn, open Métricas, assert the panel's `scrollWidth <= clientWidth`. Run `make e2e` → it fails. Red commit `test(e2e): metrics panel reflows at 320 px (red)`.
- [ ] **Step 2:** fix, run `make check-web` and `make e2e`, then commit `fix(web): let metrics values wrap at 320 px`.

### Task 11 (cut 1): real-model load test
- [ ] **Step 1 [ASK $ ≈ $1.40: a boot plus 5 min on H100]:** against the demo app with its real limits, `make loadtest ARGS="--host <demo url> -u 10 -r 0.08 -t 5m"`.
  - The spawn rate is 0.08/s because the per-IP login limit is 5/min. The chat overall limit of 200 per 600 s caps the run at about 0.33 turns/s, so it measures latency under about 10 concurrent conversations, not throughput.
  - Record p50/p95, tokens/s from the vLLM log and the GPU cost of the run, then stop the containers.
- [ ] **Step 2:** add the row to `docs/scaling-and-cost.md`. Commit `docs(loadtest): real-model load test on H100`.

### Task 12: spec sync, PR, review, owner checkpoint
- [ ] **Step 1:** commit `docs(spec): record phase 6 rulings and measured numbers`. It covers:
  - **§5:** the chosen GPU and weights with the measured table (from `docs/scaling-and-cost.md`); the cold start before/after per technique against the 30 s target; whether the client IP was confirmed on Modal; the deploy shape (two apps, `max_containers=1` on the API, scaledown 600 s, TTL 540 s).
  - **A new §7.2.5 "Phase 6 rulings":**
    - the owner decisions;
    - the served model name kept as `google/gemma-4-31B-it`;
    - the vLLM URL resolved at runtime (never in git);
    - ingestion runs from the API image, so ingest and query share the baked e5 files. This replaces the §7.2.2 "revision pinned" note: fastembed cannot pin a revision, so the image is the pin.
    - name masking (all CSV names, over-redaction accepted);
    - the stable salt;
    - `RATE_LIMIT_MULTIPLIER` (fake only);
    - the snapshot outcome;
    - what was cut.
  - **§7.3.1:** the new `cost_basis` sentences (`GPU_UPPER_BOUND`, `LOCAL`); `mode: local_cpu` is now real.
  - **§7.5:** the Gemma cost is a GPU-seconds upper bound; load test results and the bottleneck.
  - **§7.14:** `PROVIDER=local` as built, and the line-481 fix "(any of these modes)" from verdict PR-6 row 15.

  Update `AGENTS.md` (commands `deploy-llm`, `deploy-api`, `loadtest`, `PROVIDER=local`; gotchas: paid steps, never recreate `emporio-langfuse`, `HF_HUB_OFFLINE` in the image).
- [ ] **Step 2:** `make check`, `make check-web`, `make test-pg` and `make e2e` all green. Run `gitleaks` over the branch, then `git grep -nE 'https://[a-z0-9-]+--[a-z0-9-]+\.modal\.run|/(Users|home)/[a-z]'`, which must be empty (no workspace URL or local path; the plain words in this plan do not match).
- [ ] **Step 3:** `git push -u origin feat/deploy` **only when the owner says so**. Then `gh pr create`, with an English body (the measured tables, the cut items, the owner actions taken) ending in `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 4:** run the project's `reviewing-changes` skill (`.claude/skills/reviewing-changes/`) on the PR, and apply the FIX-NOW items as new commits.
- [ ] **Step 5:** owner checkpoint before merging. Bring:
  - the demo URL (in chat only, not in git) and a screenshot of a live reply with Métricas open;
  - the GPU and cold-start tables;
  - the load test numbers and bottleneck;
  - the Langfuse Cloud trace showing masked names;
  - the Modal credit spent;
  - what was cut.
