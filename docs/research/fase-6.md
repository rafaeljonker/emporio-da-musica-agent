# Phase 6 research: GPU sizing, cold start, deploy and scale

Date: 2026-11-06. Versions were fetched that day from `https://pypi.org/pypi/<name>/json` and the GitHub releases API. Service behaviour was checked against official docs on that date. Anything not verified is marked "unconfirmed", and numbers that come from arithmetic rather than measurement are marked "estimate". Nothing was run on Modal or Railway for this research. Local facts cite repo paths.

| Package / service | Version | Note |
|---|---|---|
| modal | 1.6.3 (2026-10-27) | `@app.server` (new), `@modal.asgi_app`, `@modal.concurrent`, `Image.uv_sync` |
| vllm | 0.33.0 (2026-11-02) | the Gemma 4 recipe needs ≥ 0.19.1; Modal's examples pin 0.21.0 and 0.13.0 |
| langfuse | 5.2.0 (2026-11-05) | already pinned `>=5.2.0` in `backend/pyproject.toml` |
| psycopg-pool | 3.3.3 | already used (`emporio/db.py`, pools of 1..4) |
| fastembed | 0.9.1 | e5 model to bake into the API image |
| locust | 2.47.0 (2026-10-21) | load test (§7) |
| ollama | v0.40.15 (2026-11-03) | `PROVIDER=local` (§6) |

## 1. Modal: prices, scaling knobs and limits
- **GPU prices** (https://modal.com/pricing, read 2026-11-06), per second, converted to per hour:

  | GPU | $/s | $/h | Hours on the $30 monthly credit |
  |---|---|---|---|
  | L40S (48 GB) | 0.000542 | 1.95 | 15.4 |
  | A100 80 GB | 0.000694 | 2.50 | 12.0 |
  | H100 SXM (80 GB) | 0.001097 | 3.95 | 7.6 |
  | H200 SXM (141 GB) | 0.001261 | 4.54 | 6.6 |

  CPU is $0.0000131 per physical core per second, and memory is $0.00000222 per GiB per second. A GPU container that holds 64 GiB of host RAM while loading 31B weights adds about $0.51/h of memory, which is not negligible on an L40S (estimate; the actual RAM footprint is unmeasured). Region pinning costs 1.15x (broad, `us`/`eu`/`sa`) to 1.75x (narrow), and non-preemptible execution costs 3x. Leave both at the default.
- **Free credits:** the Starter plan "includes $30 of compute (GPUs, CPUs, Memory) per month" (pricing FAQ). Whether the owner's account still has this month's credit is unconfirmed; check it in the dashboard before deploying.
- **Scale knobs** (https://modal.com/docs/guide/cold-start): the `scaledown_window` default is 60 s, the range is 2 s to 20 min, and the autoscaler "may scale down sooner" when over-provisioned. `min_containers` sets a floor (the business-hours option), and `buffer_containers` keeps spare containers while active.
- **Concurrency** (https://modal.com/docs/guide/concurrent-inputs): `@modal.concurrent(max_inputs=N, target_inputs=M)`. Sync functions run concurrent inputs on threads, async ones on one event loop.
- **Two ways to serve vLLM:**
  - `@modal.web_server(port, startup_timeout)` plus `@modal.concurrent`, used by the vLLM snapshot example (https://modal.com/docs/examples/vllm_snapshot);
  - the newer `@app.server(...)` with `startup_timeout`, `target_concurrency` (a soft autoscaling target), `max_concurrency` (a hard limit that answers 429), `routing_region`, and `unauthenticated`. It requires a Modal proxy token by default, and memory snapshots are supported (https://modal.com/docs/guide/servers, used by https://modal.com/docs/examples/vllm_inference). Its beta status is not stated.
  The spike used the first form, and the code already authenticates to vLLM with `VLLM_API_KEY`. Keep `@modal.web_server` and avoid a migration under deadline.
- **Request timeout** (https://modal.com/docs/guide/webhook-timeouts): 150 s per HTTP request. After that Modal answers 303 to a result URL, and browsers follow up to 20 redirects. The warm-up probe already treats 303 and timeouts as "still starting" (§7.2.4). A chat turn is far below 150 s.
- **ASGI app** (https://modal.com/docs/guide/webhooks): `@modal.asgi_app()` returns the FastAPI object, so `create_web_app()` from `emporio/web.py` can be returned as is. The example reads the client IP from `request.client.host`, which suggests Modal fills the ASGI client with the caller's address. That is unconfirmed: verify it once on the deployed app (verdict PR-6 row 21). Modal runs the ASGI app itself, not through our uvicorn command, so `--proxy-headers` does not apply there. New accounts are limited to 200 requests/s (429 above).
- **Region:** `routing_region` options are `us-east` (default), `us-west`, `eu-west` and `ap-south`. There is no South America routing region (https://modal.com/docs/guide/region-selection). Keep `us-east` and put the Railway database in a US East region, so the API reaches the database in a few ms and not across an ocean (the Railway region is unconfirmed).
- **Images** (https://modal.com/docs/sdk/py/latest/Image, https://modal.com/docs/guide/images): `Image.uv_sync(uv_project_dir, frozen=True, groups=...)` installs from `uv.lock`; `add_local_dir(..., copy=True)` bakes files into a layer (needed for `frontend/dist` if a later build step must see it; otherwise a runtime mount is fine); `run_function` runs a build step, which can download the e5 model into the image (closes the §7.2.3 deferral). fastembed takes a `cache_dir` (`emporio/embeddings.py`), so point it at an image path.
- **Secrets:** the existing pattern is named Modal secrets (`emporio-vllm`, plus `emporio-db` proposed in phase 3). Add `emporio-web` (`DEMO_*`, `SESSION_SECRET`, `LANGFUSE_*` incl. a stable `LANGFUSE_SALT`).
- **Custom domain:** not needed; the `*.modal.run` URL goes in the delivery e-mail.

## 2. GPU memory snapshots
- **Status:** "alpha". Enabled with `enable_memory_snapshot=True` plus `experimental_options={"enable_gpu_snapshot": True}`. Work done in `@modal.enter(snap=True)` is captured; `snap=False` hooks run after every restore (https://modal.com/docs/guide/memory-snapshot).
- **Documented limits:**
  - multi-GPU is generally incompatible (we use one GPU);
  - snapshots "do not speed up loading weights from storage";
  - `torch.compile` can break snapshot creation (`TORCHINDUCTOR_COMPILE_THREADS=1` helps);
  - each GPU type needs its own snapshots (2–3 per type), and the speedup appears "after a handful of cold starts (usually less than five)";
  - a redeploy invalidates the snapshots;
  - deleting files from a Volume used at restore breaks restores.
- **vLLM recipe** (https://modal.com/docs/examples/vllm_snapshot, Ministral 3 8B, H100, vLLM 0.13.0):
  - env `VLLM_SERVER_DEV_MODE=1` and `TORCHINDUCTOR_COMPILE_THREADS=1`; flag `--enable-sleep-mode`; KV sized down (`--max-num-seqs 2`, `--max-model-len 12288`);
  - the `snap=True` hook starts `vllm serve` as a subprocess, waits for readiness, sends three warm-up chats, then calls `POST /sleep?level=1`;
  - the `snap=False` hook calls `POST /wake_up` and waits again.
  The page claims up to "a factor of 10" and gives no measured numbers.
- **What this means for 31B:** sleep level 1 offloads the weights to host RAM, so the snapshot holds about 33 GB of FP8 weights (estimate) plus process state. Restore time for a snapshot that size is undocumented. It may still beat a cold load (no compile, no CUDA graphs, no Python import), but no source shows it for a 30B-class model, and the example is an 8B. `--max-num-seqs 2` in the recipe also caps concurrency. Raise it for us, and measure.
- **vLLM sleep-mode interaction:** with sleep mode, `/health` returns 200 while asleep (https://docs.vllm.ai/en/latest/serving/online_serving/). Our warm probe treats 200 as `ready`, which stays correct only because the `snap=False` hook wakes the engine before Modal routes traffic.

**Recommendation:** treat the GPU snapshot as the third cut item (spec §7.9). Do it only after FP8 + compile cache are measured, with a 90-minute time box, and record the failure honestly in the README if it does not work for 31B.

## 3. vLLM: Gemma 4 31B in FP8 at 16k
- **Support:** the vLLM recipe for `google/gemma-4-31B-it` says "vLLM 0.19.1+". Tool calling uses `--enable-auto-tool-choice --tool-call-parser gemma4 --chat-template examples/tool_chat_template_gemma4.jinja`, plus `--reasoning-parser gemma4` for thinking (https://recipes.vllm.ai/Google/gemma-4-31B-it). The recipe lists 31B BF16 on 2× A100/H100, and FP8 "on Hopper and Blackwell". It does not list L40S. The spike flags lack `--chat-template` and `--reasoning-parser`. Whether the spike's vLLM version bundled a working default template is unconfirmed, so pin the version and keep the spike's flags unless evals regress.
- **FP8 options:**
  - **pre-quantized:** `RedHatAI/gemma-4-31B-it-FP8-dynamic` (the recipe's pointer) or `RedHatAI/gemma-4-31B-it-FP8-block` (128×128 block weights, dynamic activations; vision tower, embeddings and LM head stay BF16; Apache-2.0; released 2026-04-04; https://huggingface.co/RedHatAI/gemma-4-31B-it-FP8-block). The block card reports recovery vs BF16 of 99–104% without thinking. With thinking, BFCLv4 Agentic recovers only **85.9%**, which is the tool-calling benchmark. We run without thinking, but tool use is exactly what our evals score, so the 22-case eval must pass on FP8 before it becomes the default.
  - **online:** current docs name the flag `--quantization fp8_per_tensor` and say "latency improvements are limited in this mode" (https://docs.vllm.ai/en/latest/features/quantization/llm_compressor/fp8/). It still downloads and reads the 62 GB BF16 weights at every cold start, which defeats the cold-start goal. Skip it.
  - **hardware:** "FP8 computation is supported on NVIDIA GPUs with compute capability >= 8.9 (Ada Lovelace, Hopper, Blackwell)", so L40S (Ada, sm_89) qualifies in general. Whether the block-FP8 kernels run fast on Ada is unconfirmed; the `-dynamic` (per-channel) checkpoint is the safer pick for an L40S run.
- **Architecture** (config.json of `google/gemma-4-31B-it`): 60 layers, of which 50 are sliding-window (window 1024, 16 KV heads, head dim 256) and 10 are global (4 KV heads, head dim 512); `attention_k_eq_v: true`; hidden 5376; vocab embedding about 1.4B params.
- **Memory estimate** (arithmetic, not measured; vLLM prints the real "maximum concurrency for N tokens" at boot):
  - weights: about 29B FP8 linear params ≈ 29 GB, plus about 2.8 GB BF16 embeddings, plus about 1 GB BF16 vision tower ≈ **33 GB**;
  - KV per token, BF16, counting K and V separately: global layers 10 × 4 × 512 × 2 × 2 B ≈ 80 KiB; sliding layers 50 × 16 × 256 × 2 × 2 B ≈ 800 KiB, capped at 1024 tokens ≈ 0.8 GB per sequence;
  - one sequence at a full 16k ≈ 1.3 GB (global) + 0.8 GB (sliding) ≈ **2.1 GB**; a typical 3k conversation ≈ 1.1 GB; `--kv-cache-dtype fp8` "saves ~50% KV memory" (recipe);
  - **L40S 48 GB** at `--gpu-memory-utilization 0.92`: about 41 GiB usable, minus 33 GB weights and about 2–3 GB activations and graphs, leaves about **5–6 GB of KV**. That is about 2–3 full-16k sequences, or about 5 typical ones (double that with FP8 KV);
  - **H100 80 GB:** about 73 GiB usable leaves about **35 GB of KV**, so about 16 full-16k sequences or about 30 typical ones.
- **Decode speed** (estimate, memory-bandwidth bound: each output token reads about 33 GB of weights):
  - L40S at 864 GB/s caps out near 26 tokens/s, so a 60–100-token reply needs about 2.5–4 s of decode alone, before the guard call and prefill. L40S will probably miss the "median ≤ 3 s" criterion. Measure it anyway (cheap, see §8), since the spec makes the comparison mandatory.
  - H100 at 3.35 TB/s caps near 100 tokens/s, faster than the spike's H200 BF16 (4.8 TB/s ÷ 62 GB ≈ 77 tokens/s). H100 FP8 should match or beat the 2.2 s median.
- **Prefix caching:** the docs say how to enable it but not the V1 default. A third-party post says it is on by default (https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/, unconfirmed). Pass `--enable-prefix-caching` explicitly; it caches the long fixed system prompt and tool schemas across turns. Gemma 4 sliding layers complicate prefix reuse (hybrid KV manager); check the hit rate in the vLLM metrics log (`VLLM_LOG_STATS_INTERVAL`) instead of assuming.
- **Compile cache and CUDA graphs:**
  - vLLM stores compile artifacts under `~/.cache/vllm/torch_compile_cache/<hash>/`, and a repeat boot "directly loads" the graph. The cache key covers configs, PyTorch config and the traced model code (https://docs.vllm.ai/en/latest/design/torch_compile/).
  - Modal mounts a `vllm-cache` Volume at `/root/.cache/vllm`, and says compilation takes "tens of seconds to a few minutes, reduced to about ten seconds when loaded from the cache" (https://modal.com/docs/examples/vllm_inference).
  - `--enforce-eager` "disables both Torch compilation and CUDA graph capture": the fastest boot, but slower decode. Modal suggests it (`FAST_BOOT`) for services that often scale from zero.
  - CUDA-graph capture can be trimmed with `--compilation-config '{"cudagraph_capture_sizes": [1, 2, 4, 8]}'`, which fits our low concurrency.
- **`/health`:** listed as a health check; its exact semantics and `--api-key` exemption are not documented (unchanged from the phase 5 research). Keep sending the bearer.
- **Expected cold-start breakdown** (175 s measured on H200 BF16, split by estimate only; step one of the spec is to log real timestamps): container start and image about 10–20 s; reading 62 GB of weights from the HF-cache Volume about 60–90 s; `torch.compile` about 30–60 s (cache cold); CUDA graph capture about 10–20 s; API server up about 5 s.

  | Optimization (spec §5) | Expected saving (estimate) | Cost |
  |---|---|---|
  | 1. FP8 checkpoint (33 GB instead of 62 GB) | −30 to −45 s | eval risk (BFCLv4 Agentic 85.9%) |
  | 2. 16k context + compile cache on a Volume | compile from about 45 s to about 10 s after the first boot; smaller KV profiling | first boot still pays |
  | 2b. fewer CUDA-graph sizes, or `--enforce-eager` | −10 to −20 s, or the whole compile and graph share | eager: slower decode, measure latency |
  | 3. GPU memory snapshot | up to "10×" per Modal; unproven for 31B | alpha, snapshot of about 33 GB, 3–5 boots to settle |
  | 4–5. warm-up on login + honest screen | perceived wait | already built (phase 5) |

  With 1 + 2 a realistic target is about 60–90 s on H100 (estimate). The spec's **≤ 30 s target probably needs the snapshot**. That makes the snapshot more valuable than its cut position suggests, and also the riskiest item (§ Risks).

**Recommendation:** pin vLLM (0.33.0 or the newest version the spike app builds with), serve the FP8 checkpoint from the HF-cache Volume with `--max-model-len 16384 --enable-prefix-caching --kv-cache-dtype fp8 --gpu-memory-utilization 0.92`, add a `vllm-cache` Volume, log boot timestamps, and run the eval on H100 first, then on L40S.

## 4. FastAPI app on Modal (CPU) with Railway Postgres and Langfuse Cloud
- **Shape:** one `@app.function(image=api_image, secrets=[...], max_containers=1, scaledown_window=...)` with `@modal.concurrent(max_inputs=100)` and `@modal.asgi_app()`, returning `emporio.web.create_web_app()`. **`max_containers=1` is required**: rate limits, thread locks and the warm-up state are per process (AGENTS.md gotcha, `api/guards.py` ponytail note).
- **Threads:** `/api/chat` streams from a sync generator, which FastAPI runs in the AnyIO thread pool (default 40 tokens). So at most about 40 turns run at once per container, whatever `max_inputs` says. This is the probable first bottleneck under load, and it is a README finding, not a fix.
- **DB pool:** `make_pool` defaults to 1..4 connections (`emporio/db.py`), and the checkpointer has its own pool. Hundreds of concurrent turns will queue on 4 connections (30 s pool timeout). Under the fake-model load test this shows as latency, not errors; raise `max_size` only if the test shows it.
- **Railway** (phase 3 research §6 still holds): the default Postgres image ships pgvector (verify `pg_available_extensions`). From Modal use the public TCP proxy (`DATABASE_PUBLIC_URL`) with `sslmode=require`. Proxy traffic is billed as egress (https://docs.railway.com/guides/postgresql). Do not enable app sleeping. Run `make migrate ingest` once against Railway from the laptop. `build_agent` also migrates at boot, which is idempotent.
- **Stale connections:** a Modal container idles between requests, and a proxied TCP connection may be cut meanwhile. Railway documents no idle timeout. psycopg_pool's `check=ConnectionPool.check_connection` (a test query on checkout) is the one-line guard if the first request after idle fails (unconfirmed need; add it only on evidence).
- **Langfuse Cloud:**
  - the SDK v5 reads `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` and `LANGFUSE_BASE_URL`; EU is `https://cloud.langfuse.com` (the default) and US is `https://us.cloud.langfuse.com` (https://langfuse.com/docs/observability/sdk/overview);
  - the Hobby plan gives 50k units/month, 30 days of data, 2 users, ingestion 1,000 req/min, the general API 30 req/min, and EU/US/Japan regions (https://langfuse.com/pricing);
  - `config.py` already forces sampling to 1 and checks auth at boot;
  - **phase 6 gates before pointing at Cloud:** (a) mask the customer's first name in spans (today `tracing.py` masks e-mail and phone only); masking against the known customer names from the CSV is deterministic; (b) a stable `LANGFUSE_SALT` in the Modal secret, or pseudonyms change on every deploy.
- **Flush:** short-lived containers must flush. `build_agent` registers shutdown hooks (phase 4). Confirm that Modal's container exit runs the ASGI lifespan shutdown (unconfirmed); add an `@modal.exit` flush if traces go missing.
- **`WARM_READY_TTL_SECONDS`:** set it a little under the vLLM function's `scaledown_window` (for example window 600 s, TTL 540 s), so a `ready` older than the window is probed again.
- **Verdict leftovers that must land before a public URL:** `/docs` and `/openapi.json` are unauthenticated (PR-6 row 13: set `docs_url=None, redoc_url=None, openapi_url=None`), and the client-IP check (row 21). Row 1 (chat cap bypass) is already closed by the overall chat window in `api/chat.py`.

**Recommendation:** one ASGI function pinned to one container, an image built with `uv_sync` and the e5 model baked in, `frontend/dist` added at deploy, Railway over the TLS proxy, and Langfuse Cloud EU after the two gates.

## 5. Cost model
- **Scale-to-zero demo, per evaluator session** (estimate): H100 with about 60 s cold start, 10 min of use and a 10 min scaledown window is about 21 GPU-min, or **about $1.40**; the same on L40S is about $0.70. The idle window is most of it. A 5 min window saves about a third but makes a second cold start likelier for a slow evaluator.
- **Marginal cost per conversation at concurrency 1:** a conversation of about 4 turns × 2.2 s ≈ 9 GPU-s, so H100 ≈ $0.010 and L40S ≈ $0.005 (L40S will be slower, so more seconds). With continuous batching at concurrency C the cost divides by about C, so it is negligible on a busy GPU.
- **Always-on options for the README** (spec: explained, not enabled):

  | Option | Hours/month | H100 | L40S |
  |---|---|---|---|
  | Store hours (Mon–Fri 9–18, Sat 9–13 ≈ 49 h/week) | ≈ 212 | ≈ $837 | ≈ $414 |
  | 24/7 | 730 | ≈ $2,883 | ≈ $1,424 |

  One H100 at about 30 concurrent sequences serves about 10 turns/s (estimate), and 100k conversations/month averages 0.04 conversation/s. **The 1k, 10k and 100k projections all fit on one GPU**, so the self-hosted cost is flat (the hours above), not per conversation. Scaling past one GPU means more replicas (`max_containers`), a queue, or a larger GPU, and only far above 100k.
- **API providers, list prices** (read 2026-11-06), per 1M tokens (input / cached input / output):
  - `gemini-3.8-flash`: $0.75 / $0.075 / $3.75 until 2026-12-31, then $1.50 / $0.15 / $7.50; a free tier exists (https://aistudio.google.com/docs/pricing);
  - `claude-haiku-5-5`: $0.10 / $0.01 / $0.50 for prompts ≤ 100k (https://claude.com/pricing);
  - `gpt-6-luna`: $0.10 / $0.01 / $0.50 for context ≤ 272k (https://developers.openai.com/api/docs/pricing).

  The Haiku and Luna figures match `config.py`. **`gemini-3.8-flash` is missing from `Settings.prices`**, so a Gemini turn reports a `null` cost today; add it, with the 2027 price change noted.
- **Per-conversation API cost** at about 1,800 input + 200 output tokens (spike tokens/conversation ≈ 2,000; estimate): Gemini ≈ $0.0021, Haiku and Luna ≈ $0.00028. At 100k conversations/month: Gemini ≈ $210, Haiku/Luna ≈ $28.
- **Honest conclusion for `scaling-and-cost.md`:** at these volumes a cheap API model costs one to two orders of magnitude less than a dedicated GPU. Self-hosting Gemma is justified by voice quality (model-selection rounds 1–3), data control and no per-token dependency, not by cost. The break-even with Gemini Flash at store hours is about 400k conversations/month on H100 (estimate).
- **Gemma cost in `turn_metrics`** (deferred to phase 6 by §7.5): an honest per-turn number is `ms_llm × $/s` of the GPU, labelled an upper bound at concurrency 1, with `cost_basis = "gpu_seconds_upper_bound"`. It needs one config price per GPU type.

## 6. `make up PROVIDER=local` (Ollama)
- **Models** (https://ollama.com/library/gemma4/tags): `gemma4:31b` (q4_K_M about 20 GB, 256K ctx; `31b-it-qat` 19 GB; `31b-it-q8_0` 34 GB), `gemma4:12b` (q4 about 8 GB), `gemma4:e4b` (about 6.6–9.5 GB, 128K) and `gemma4:e2b`. The family carries the tools, thinking and vision badges; per-tag capabilities are not listed.
- **OpenAI-compatible** at `http://localhost:11434/v1/` (the key is ignored but must be non-empty); `/v1/chat/completions` supports `tools` (https://docs.ollama.com/api/openai-compatibility). The factory can reuse the OpenAI-compatible client path with a different `base_url`, which is a new `Provider.LOCAL` with `OLLAMA_BASE_URL` and `OLLAMA_MODEL`.
- **Context trap:** "The OpenAI API does not have a way of setting the context size". The doc's way is a Modelfile with `PARAMETER num_ctx`. Our prompt plus tool schemas is about 3k tokens and grows with history. The server-wide `OLLAMA_CONTEXT_LENGTH` env var is not on that page (unconfirmed for v0.40); a Modelfile (`FROM gemma4:31b` + `PARAMETER num_ctx 16384`, then `ollama create emporio-gemma`) is the documented route.
- **Docker** (https://docs.ollama.com/docker): CPU is `docker run ... ollama/ollama`; NVIDIA adds `--gpus=all` and needs the NVIDIA Container Toolkit. Docker on macOS has no Metal access, so Apple Silicon uses the native app (spec §7.14). A compose `ollama` profile with a GPU `deploy.resources.reservations.devices` block covers NVIDIA (compose syntax not on that page; standard Docker Compose).
- **Detection** (shell, in the Makefile preflight): `uname -sm` = `Darwin arm64` → native (check `ollama` on PATH, else print the install link and stop); `nvidia-smi` succeeds and `docker info` lists the `nvidia` runtime → Docker GPU; otherwise Docker CPU. Memory: `sysctl -n hw.memsize` (mac) or `/proc/meminfo`. Size rule: 31B with a GPU or a Mac with ≥ 32 GB; else `gemma4:12b` (about 8 GB) at ≥ 16 GB RAM; else `gemma4:e4b`.
- **Expectations** (estimates, CPU decode is RAM-bandwidth bound, about 50–100 GB/s on laptops): 31B q4 on CPU about 2–4 tokens/s, so 30 s to minutes per turn; 12B q4 about 5–10 tokens/s; e4b about 10–20 tokens/s. On an M-series Mac with 32 GB+, 31B q4 is about 8–15 tokens/s. These go in the three warnings (terminal, README, loading screen), with "measured on" added only for machines actually tried.
- **Quality:** the smaller variant has never run the evals. Running `make evals PROVIDER=local` once on the owner's Mac gives the README row.

**Recommendation:** `Provider.LOCAL` over the existing OpenAI-compatible path, a Modelfile pinning `num_ctx 16384`, shell detection in the preflight, three warnings, and one eval run on the owner's machine.

## 7. Load testing
- **Locust vs k6:**
  - Locust 2.47.0 is Python, which fits the "backend 100% Python" rule.
  - k6 scripts are JavaScript, and SSE needs the `xk6-sse` extension build.
  - **Pick Locust.** Plain `HttpUser` (requests) reads the whole body, so the reported time is the full SSE turn. `FastHttpUser` with `stream=True` excludes body time ("the time for downloading the response content will not be accounted for", https://docs.locust.io/en/stable/increase-performance.html), so avoid it for SSE. Each simulated user logs in once in `on_start` (the session keeps the cookie), switches to a demo customer, then posts turns and parses `event: done`/`error`.
- **Our own limits will throttle the test before Modal does** (hard-coded in `api/auth.py`, `api/chat.py`):
  - login is 5/min per IP and 30/min overall, and all Locust users share one IP;
  - chat is 200 per 600 s overall, about 0.33 turn/s sustained;
  - "hundreds of simultaneous conversations" therefore need these windows to be configurable by env and raised **only on the fake-model deployment**.
- **Fake-model deployment:** a second Modal app (for example `emporio-api-loadtest`) from the same code with `EMPORIO_FAKE_MODEL=1`, raised limits, no `emporio-vllm` secret, and `max_containers=1`, so it can never wake the GPU. It measures our infra: threads, DB pool, Railway round trips and Modal proxying. Delete it after the run.
- **Langfuse budget:** sampling is forced to 1, and the Hobby plan has 50k units/month. A fake turn emits roughly 5–15 observations (unconfirmed; count one), so 300 users × 5 turns ≈ 7.5k–22k units. Run the fake test once, sized from a counted trace, or point the load-test deployment at a second Langfuse project. Whether units are per organization or per project is unconfirmed; assume per organization.
- **Real-LLM mode** (cut item 1): about 10–20 users for 5 min on the H100 app ≈ $0.35 GPU plus Langfuse units; it gives real p50/p95 and tokens/s under batching.
- **Railway egress** is billed on the proxy; a fake run moves little data (cost unconfirmed, likely cents).

**Recommendation:** Locust `HttpUser` with login in `on_start`, env-tunable rate windows, a throwaway fake-model Modal app, and one small real-LLM run if time allows.

## Proposed task breakdown (about one working day)
Order follows dependencies; times are estimates. The spec's cut order applies from the bottom: real-LLM load test first, metrics panel (already built in phase 5, so nothing to cut), GPU snapshot last. Langfuse is never cut.

1. **vLLM Modal app in the repo** (`deploy/modal_llm.py`): GPU type from an env var, FP8 checkpoint downloaded to the HF-cache Volume by a one-off function, `vllm-cache` Volume, pinned vLLM, 16k, prefix caching, FP8 KV, the gemma4 tool parser, `@modal.web_server` with a 10 min `startup_timeout`, boot-stage timestamps logged, `scaledown_window` chosen (D2). 1.5 h.
2. **Measure:** cold start ×2 per GPU (cache cold and warm), 22-case evals and latency p50 on H100 FP8, then on L40S FP8; one row each in the README table. About 1.5 h, mostly waiting; about $3–6 of credit.
3. **Langfuse Cloud gates (TDD):** first-name masking in `mask_otel_spans` against the CSV customer names, a stable `LANGFUSE_SALT` in the Modal secret, then one checked trace on Cloud EU. 1 h.
4. **API on Modal** (`deploy/modal_api.py`): `uv_sync` image, e5 baked with a pinned cache dir, `frontend/dist`, secrets, `max_containers=1`, docs routes off, `WARM_READY_TTL_SECONDS` tied to the GPU window, Railway migrate and ingest, `gemini-3.8-flash` price in `Settings.prices`, one client-IP log check. 2 h.
5. **Fake-model load test:** env-tunable rate windows (TDD), `loadtest/locustfile.py`, throwaway fake deployment, one run at 100–300 users, numbers and the identified bottleneck for the README. 1.5 h.
6. **Cost:** GPU-seconds upper-bound cost in `turn_metrics` (TDD, small), the cost table and projections drafted for `scaling-and-cost.md`. 45 min.
7. **`make up PROVIDER=local`:** `Provider.LOCAL`, Modelfile, detection script, three warnings, one eval run on the owner's Mac. 2 h.
8. *(cut 1)* Real-LLM load test, 10–20 users, 5 min. 45 min.
9. *(cut 3, time-boxed)* GPU memory snapshot with sleep mode; measure restore over 3–5 boots. 1.5 h.

Core (1–7) ≈ 10.5 h, with 8 and 9 on top. That is over one day, so either D5 (a lean `PROVIDER=local`) or cutting 8 and 9 is needed.

## Decisions to confirm with the owner
1. **GPU for the demo:** H100 FP8 (recommended: probably the only one meeting median ≤ 3 s; $3.95/h, about $1.40 per evaluator session) or L40S FP8 ($1.95/h, about 26 tokens/s ceiling, likely 3–5 s per reply). Both are measured either way; the choice is the default. A wrong pick costs a redeploy (minutes).
2. **`scaledown_window` for the GPU:** 10 min (recommended: an evaluator who pauses to read does not hit a second cold start; about $0.65 idle per session on H100), 5 min (half the idle cost, more cold starts), or 20 min (the max).
3. **FP8 checkpoint:** `RedHatAI/gemma-4-31B-it-FP8-dynamic` (recommended: the vLLM recipe's pointer, per-channel kernels also fine on Ada) or `-FP8-block` (the card with published evals, BFCLv4 Agentic 85.9%). If evals drop below 14/14 effective, does the default fall back to BF16 on H100 (62 GB, slower cold start) or stay FP8 with the regression documented?
4. **GPU memory snapshot effort:** time-box it to 90 min after everything else (recommended; alpha, unproven at 31B, but likely the only path to ≤ 30 s), or skip it and document the measured FP8 + cache number against the 30 s target.
5. **`PROVIDER=local` scope:** lean (recommended, about 2 h: macOS native + Docker CPU + Docker NVIDIA detection, three warnings, one eval run on your Mac, other hardware rows marked "estimate"), or full (an eval per size variant, about +1.5 h).
6. **Load test and Langfuse budget:** a fake-model run of 100–300 users on a throwaway deployment with raised limits, into the same Langfuse Cloud org sized from one counted trace (recommended), or a separate Langfuse project/org for load (cleaner demo data, one more account), and a real-LLM run of 10–20 users only if time is left (about $0.35).

## Risks
- **FP8 tool-calling regression:** the FP8 card's own BFCLv4 Agentic recovery is 85.9%. If our evals drop, the cheap path is gone, and BF16 needs ≥ 80 GB (H100 is tight at 62 GB of weights plus KV) or the H200 again.
- **The 30 s cold-start target** is likely unreachable without the GPU snapshot, which is alpha, unproven for a 33 GB snapshot, and needs 3–5 boots to settle (each boot is GPU money).
- **Credits:** $30/month is about 7.6 H100 hours. Measurement, the snapshot boots, a real-LLM load test and a weekend of evaluator sessions can exhaust it. The spec says no spending cap, so set a budget alert in the dashboard.
- **Per-process state** forces `max_containers=1` on the API; the AnyIO thread pool (40) and DB pool (4) cap concurrent turns there. That is acceptable for the demo and is what the load test should expose.
- **Our own rate limits and Langfuse units** will distort the load test unless the fake deployment raises them and the run is sized.
- **Client IP behind Modal** is unconfirmed. If `request.client.host` is the proxy, the per-IP login limit is effectively the overall one (already backstopped).
- **Railway region and egress:** a database far from Modal's `us-east` adds a round trip to every turn; the public proxy is billed and exposed to the internet (strong generated password, never committed).
- **Ollama context:** without a Modelfile `num_ctx`, a local model can silently truncate the prompt and tools, which shows up as a "dumb model", not an error.
- **Deadline:** core tasks are about 10.5 h. Cut in the spec's order and never Langfuse, the deploy or the README numbers.

## Owner decisions
Decided by the owner on 2026-11-06:
1. **GPU and weights:** measure L40S and H100 with the FP8 checkpoint (`RedHatAI/gemma-4-31B-it-FP8-dynamic`), as the spec requires; default to H100 + FP8. If FP8 lowers the eval score against BF16, fall back to BF16 on H100 and document it.
2. **GPU scaledown window:** 10 min; `WARM_READY_TTL_SECONDS` about 540 s, just under it.
3. **`PROVIDER=local`:** the lean version (about 2 h): macOS native, Docker CPU and Docker NVIDIA detection, the three warnings, a Modelfile with a 16k context, one eval run on the owner's Mac.
4. **Snapshot and load test:** GPU memory snapshot time-boxed to 90 min at the end (documented either way); Locust against a fake-model app at 100–300 users; a 10–20 user real-model run only if time is left.
