# Scaling and cost

Phase 6 numbers: GPU sizing, cold start, the load test and the cost per conversation. Everything here was measured on 2026-11-06 unless it says **estimate**, in which case the basis is given next to it. The Modal budget for this phase was $8 of credit with no card on file, which is why some measurements were skipped (see "What was not measured").

Prices: Modal list prices read on 2026-11-06 (H100 $3.95/h and L40S $1.95/h from `deploy/modal_api.py` `GPU_PRICES`; H200 $4.54/h from `docs/research/fase-6.md`), Gemini list prices from `backend/src/emporio/config.py` (`Settings.prices`), and `usd_brl` 5.50 (config default).

## 1. GPU sizing

Gemma 4 31B on vLLM 0.33.0 (`deploy/modal_llm.py`): FP8 weights `RedHatAI/gemma-4-31B-it-FP8-dynamic`, `--max-model-len 16384`, FP8 KV cache, prefix caching, served as `google/gemma-4-31B-it`. Evals are the 22 golden cases (`make evals PROVIDER=...`); the reports are in `backend/evals/reports/`.

| GPU | weights | $/h | cold start (cache cold / warm) | p50 / p95 | evals pass | AI tells |
|---|---|---|---|---|---|---|
| H200 (spike baseline) | BF16 | 4.54 | 175 s (cache state not recorded) | 2.2 s median, 3.9 s max | 14/14 effective, on the 14-case spike suite | 0 |
| H100 | FP8 | 3.95 | 381.7 s / 273.1 s (multimodal on); ~204 s observed later with multimodal off | 2.05 s / 4.11 s | 21/22 | 4 |
| L40S | FP8 | 1.95 | 310.8 s / 214.9 s (multimodal off) | 4.93 s / 9.98 s | 21/22 (22/22 effective) | 0 |
| Gemini 3.8 Flash (API) | n/a | per token | none for the model; the CPU API container's own cold start was 19 s on a first hit | 5.52 s / 9.74 s | 22/22 | 0 |

How to read the rows, honestly:
- **The H100 run is from before the voice and markup fixes.** Its 4 AI tells were 3 `too_many_bubbles` and 1 `multiple_questions`, and most replies started with the raw Gemma thinking-channel marker (`<|channel>thought<channel|>`), visible to the customer. Its one fail (`arrependimento_identificado`) was a real miss: the model did not call `check_return_eligibility`. The fixes that followed (bubbles capped at three, one question per turn, regret checks eligibility first, `--reasoning-parser gemma4` plus a code-level strip of the channel markup) were never re-evaluated on the H100, because the hosted demo moved to Gemini before that run. The H100 row's quality numbers are therefore a lower bound; its latency numbers stand.
- **The L40S run is after those fixes.** Its one fail (`devolucao_fora_do_prazo`) was a verifier false negative: the model wrote the plural "prazos ... já passaram", which the regex verifier did not accept. The verifier was fixed afterwards, so the effective score is 22/22. It was not re-run.
- **The Gemini run** is the final one, on the delivered code (catalog in Postgres, hybrid search, prompt-injection rule), with the Flash-Lite guard: 22/22. It is a single run. The run before it (same model, before the partial-search prompt rule and the last verifier fix) passed 20/22: `recomendacao_mpb` recommended valid nylon guitars from the catalog that were not the recommend tool's picks (a divergence from the recommender, not a wrong fact), and `devolucao_fora_do_prazo` explained the expired window correctly in a phrasing the regex verifier did not accept.
- **The spike baseline** used a different suite (14 cases) and an older vLLM, so it is a reference point, not a like-for-like comparison. The BF16 baseline on H100 was skipped for budget (owner decision), so FP8 vs BF16 on the same GPU and suite was never measured.
- **Tokens/s** were not recorded for either GPU run.
- **Both committed Gemma reports are pre-fix runs.** `backend/evals/reports/gemma-h100-fp8.md` and `gemma-l40s-fp8.md` predate the final verifier and bubble code (the L40S transcripts still end sentences with a period); only `gemini.md` ran on the final code. Rerun `make evals PROVIDER=gemma` before citing them as proof of the fixes on Gemma.

**Choice:** H100 FP8 is the Gemma default (`emporio-llm-h100-fp8`): the L40S is half the price per hour but its median reply (4.9 s) misses the spec's ≤ 3 s, and it takes longer per reply, so it is not cheaper per reply either (section 4).

## 2. Cold start

Target from the spec: **≤ 30 s. It is not met.** The best H100 boot observed is about 204 s, slower than the spike's 175 s on H200 BF16.

Boot stages, from the `[boot +Ns]` lines that `deploy/modal_llm.py` prints:

| Boot | Total | Weights | Multimodal warm-up | Engine init | Of which: compile | CUDA graphs | FlashInfer JIT sampling | Rest (container, imports, API server) |
|---|---|---|---|---|---|---|---|---|
| H100 #1, cache cold | 381.7 s | 28 s | 61 s | 266 s | 90 s | 25 s | not split out | ~27 s (derived) |
| H100 #2, cache warm | 273.1 s | not split out | on | not split out | from cache | | | |
| H100, owner login, cache warm, multimodal off | ~204 s | not split out | off | 135 s | 1.1 s | 15 s | ~100 s | ~69 s (derived: total minus engine init) |
| L40S #1, cache cold, multimodal off | 310.8 s | not split out | off | | | | | |
| L40S #2, cache warm, multimodal off | 214.9 s | not split out | off | | | | | |

"Cold start" is `deploy/cold_start.py`: stop every container, then time from the first request until `/health` answers; the first reply after that took 0.4 s (H100) and 1.2–2.2 s (L40S).

What each technique did:

| Technique | Effect | Status |
|---|---|---|
| FP8 checkpoint (~33 GB instead of ~62 GB) | weights load in 28 s on H100 | kept. Its saving against BF16 on the same GPU was not measured (BF16 baseline skipped) |
| 16k context + `torch.compile` cache on the `vllm-cache` Volume | compile 90 s → 1.1 s; H100 381.7 s → 273.1 s cache cold vs warm | kept |
| `--language-model-only` (text only: no multimodal processor) | removes the ~61 s multimodal warm-up | kept; 273 s → ~204 s between the two H100 cache-warm boots (other things changed too: the reasoning parser) |
| FlashInfer JIT sampling kernels | ~100 s on every boot: compiled at boot and **not cached** on the Volume | the largest remaining stage |
| GPU memory snapshot | not tried | skipped for budget (owner decision: $8 credit, no card) |
| Warm-up on login + the explanatory loading screen (phase 5) | the GPU starts when the evaluator logs in, not on the first message | kept; lowers the perceived wait, not the boot |

What would meet 30 s, in order of expected payoff (none of it measured):
1. **GPU memory snapshot** (Modal, alpha): restores a booted vLLM, so compile, JIT and CUDA graphs are skipped. Unproven for a 31B model (about a 33 GB snapshot) and needs several boots to settle, each one paid.
2. **Cache the FlashInfer JIT directory on the Volume**, like the compile cache: about −100 s per boot (estimate: the observed stage time), still far from 30 s on its own.
3. **`min_containers=1` during store hours**: no cold start for customers at all, at the cost of a GPU held on (section 4: about $837/month on H100 for store hours, estimate).

## 3. Why the hosted demo runs Gemini

Owner decision (2026-11-06): the hosted demo at https://emporio.fastmind.site runs `gemini-3.8-flash` (guard on Flash-Lite). Two reasons: no GPU cold start for an evaluator (about 3.5 min on H100), and the Modal credit ($8, no card) would not cover many evaluator sessions on a GPU (section 4). Gemini passed all 22 of the same cases with 0 AI tells.

It **misses the spec's ≤ 3 s reply target**: p50 5.52 s, p95 9.74 s (the guard adds a second, sequential model call per turn). It was chosen anyway: an evaluator who meets a 3.5 min GPU cold start or a drained credit sees no reply at all, while a ~5.5 s reply still works; the H100 is the option that meets 3 s once the GPU is warm.

Gemma stays one flag away, with no code change:

```
make deploy-llm                      # emporio-llm-h100-fp8 (LLM_GPU=L40S for the other one)
make deploy-api API_PROVIDER=gemma   # the API calls the GPU app; LLM_APP picks which one
```

The vLLM URL is resolved at runtime from the deployed app, never stored in git.

## 4. Load test

### Method
- **Tool:** Locust 2.47.0, `loadtest/locustfile.py` (`make loadtest ARGS="..."`), plain `HttpUser` so the measured time includes the whole SSE body. Each virtual user logs in once, switches to a random demo customer, then posts one of five pt-BR messages every 3–8 s; a turn counts as a success only if the stream ends in `event: done`.
- **Target:** a throwaway Modal app `emporio-api-loadtest` (`make deploy-api LOADTEST=1`) with the **scripted (fake) model**, so it measures our infrastructure, not an LLM: one container (`max_containers=1`), real Railway Postgres over its TCP proxy, real Langfuse Cloud tracing, `DB_POOL_MAX=20`, and `RATE_LIMIT_MULTIPLIER=100`. The multiplier only boots together with `EMPORIO_FAKE_MODEL=1` (a config check), so raised limits can never reach a real model. The app was stopped after the runs (`make loadtest-down`). The deployed demo runs the default `DB_POOL_MAX=4`, so the figures below hold for a pool of 20, not for the demo's own throughput.
- **Load generator:** one laptop.

### The bottleneck found
The first 50-user run had a chat median of 48 s with a fake model. An in-container probe (20 turns in parallel inside one Modal container; `SELECT 1` round trip to Railway: median 82 ms) found two causes:
1. **`PostgresSaver` holds one lock around every call.** The lock exists to guard a single shared connection; on a pool each call checks out its own connection, so the lock only serialised every thread's checkpoint I/O (8 calls per turn: 1 `get_tuple`, 4 `put`, 3 `put_writes`). Fix: the saver's lock is a no-op on our pool.
2. **Pools grew one connection at a time** (`min_size=1`): each new connection over the proxy costs about a second, so turns queued behind pool growth. Fix: both pools open at full size (`DB_POOL_MAX`).

| Probe: 20 parallel fake turns | Wall time | Per-turn p50 | Note |
|---|---|---|---|
| saver lock, pool 1..4 | 15.0 s | 14.2 s | lock wait avg 3.2 s, max 6.9 s |
| no lock, pool 1..20 growing | 12.1 s | 10.1 s | pool reached 9 connections; 163 of 232 requests queued |
| no lock, pool 20..20 (the fix) | 3.4 s | 2.6 s | |

Commits: `e399098` (red test) and `00ecb94`.

### Before and after

| Run | Chats | Failures | Chats/s | Chat p50 | Chat p95 | Login p50 |
|---|---|---|---|---|---|---|
| Before, 50 users, 60 s | 35 | 0 | 0.60 | 48 s | 51 s | 1.0 s |
| After, 50 users, 60 s | 249 | 0 | 4.17 | 1.7 s | 2.7 s | 20 s (see below) |
| After, 120 users, 2 min | 1,334 | 0 | 11.2 | 4.2 s | 6.2 s | 1.1 s |

The after-50 run hit a freshly redeployed container, so its login times (17–23 s) include the API container's start and both pools opening at full size; the two were not separated. The 120-user run started warm (login p50 1.1 s).

### The next bottleneck
- **Checkpoint round trips:** about 8 sequential checkpoint calls per turn at ~80 ms each to Railway, so about 0.65 s of every turn is network wait before the model runs (derived from the measured RTT and call count).
- **One container's CPU and threads:** from 1.7 s at 50 users to 4.2 s at 120, with no failures. By Little's law, 11.2 chats/s × ~4.1 s ≈ 46 turns in flight, above the 40 threads of AnyIO's default pool that runs the sync SSE generator, so part of the 4.2 s is probably queueing for a thread (estimate, not instrumented).

### How to scale
1. **Co-locate regions:** the API runs in Modal `us-east`; an 82 ms `SELECT 1` says the database is not next to it. A database in the same region cuts the ~0.65 s per turn to a few ms (estimate).
2. **Move per-process state to a shared store** (rate limits, per-thread locks and the warm-up status live in memory today; a Postgres table or Redis), then raise `max_containers` above 1.
3. **Durability trade-off:** write the checkpoint once per turn instead of after each graph step (LangGraph's durability setting), which removes most of the 8 round trips but loses mid-turn recovery after a crash.
4. **The model:** with a real model the LLM dominates (2–7 s per turn), so the next limit is the provider's quota (Gemini) or the GPU's concurrent sequences (Gemma; one GPU via `max_containers=1` today, a cost guard).

The real-model load test (10–20 users on the H100) was skipped for budget (owner decision), so latency under GPU batching is not measured.

## 5. Cost per conversation

### Gemini (measured)
The final Gemini eval run reports **R$ 0.0292 per eval case** (about $0.0053; 6,878 input and 109 output tokens on average), with the guard's tokens priced at the Flash-Lite rate. Both rates are the list price valid until 2026-12-31 (from 2027-01-01 it doubles). A live turn on the hosted demo showed R$ 0.0255. Most eval cases are a single customer message, so a 4-turn conversation is about **R$ 0.11 ($0.020)** (estimate: 4 × the per-case cost; later turns carry more history, so this leans low).

### Gemma (upper bound vs real session)
The metrics panel prices a Gemma turn as **GPU seconds × the GPU's hourly price** (`cost_basis` "Teto pelo tempo de GPU desta resposta"): an upper bound that assumes the GPU serves only this turn (concurrency 1).
- At the measured p50 per case: H100 2.05 s × $3.95/h ≈ $0.0023 (R$ 0.012); L40S 4.93 s × $1.95/h ≈ $0.0027 (R$ 0.015). The cheaper GPU costs more per reply because it is slower.

That bound ignores what a scale-to-zero session actually pays: the boot, the idle time and the scaledown window. One evaluator session on H100 is about 204 s boot + 10 min of use + 300 s scaledown ≈ 1,104 GPU-seconds ≈ **$1.21** (estimate: observed boot, assumed 10 min of use, configured scaledown; Modal CPU and memory charges excluded). At 10 messages in that session that is about $0.12 per message, some 50 times the GPU-seconds bound. The idle and boot time, not the replies, is the cost.

### Projections (all estimates)
Assumptions: 4 turns per conversation; Gemini at the measured per-case cost; Haiku/Luna at list price ($0.10 / $0.50 per 1M tokens) with Gemini's measured token counts (their quality was not evaluated in this phase); the GPU options as Modal list price × hours (store hours Mon–Fri 9–18 + Sat 9–13 ≈ 212 h/month; 24/7 = 730 h), assuming one GPU holds the load (100k conversations/month is about 0.5 turns/s averaged over store hours; GPU concurrency was not load-tested).

| Monthly conversations | Gemini 3.8 Flash (2026 price) | Gemini 3.8 Flash (2027 price) | Haiku 5.5 / GPT-6 Luna (list) | H100, store hours (`min_containers=1`) | H100, 24/7 | L40S, store hours / 24/7 |
|---|---|---|---|---|---|---|
| 1k | ~$20 | ~$40 | ~$3 | ~$837 | ~$2,884 | ~$414 / ~$1,424 |
| 10k | ~$201 | ~$403 | ~$28 | ~$837 | ~$2,884 | ~$414 / ~$1,424 |
| 100k | ~$2,015 | ~$4,029 | ~$284 | ~$837 | ~$2,884 | ~$414 / ~$1,424 |

The GPU columns are flat (paid by the hour), and a store-hours GPU answers nobody outside store hours. Scale-to-zero sits below those figures at low traffic but adds a ~3.5 min cold start whenever the GPU is off.

### Conclusion
At 1k conversations a month an API model is one to two orders of magnitude cheaper than a dedicated GPU, and at 10k Gemini Flash is still about 4 times cheaper than a store-hours H100. With the measured Gemini token counts the break-even against a store-hours H100 is about 42k conversations/month (about 21k at the 2027 price), and about 143k against a 24/7 H100 (estimates); the cheapest API tiers stay below the GPU even at 100k. So self-hosting Gemma is not justified by cost at these volumes. It is justified by voice (the most human voice in the model selection) and control (data stays on our GPU, no per-token dependency or provider quota), and it is one flag away when that matters more than cost.

## 6. Langfuse Cloud budget

Langfuse Cloud (EU, Hobby plan: 50k units/month) traces every turn, and the load-test app shared the demo's project (no separate project was created). The test traffic sent to it was about 1,618 fake turns from Locust (35 + 249 + 1,334) plus three in-container probes of 20 parallel turns, on top of the eval runs and the demo smoke tests. Units per fake turn were **not counted**; at the research estimate of 5–15 observations plus one trace per turn, the load tests used roughly 10k–27k units (estimate). The upper bound exceeds the ≤ 20k units the phase plan allowed for load tests, and since units were not counted it may have done so; so check the usage page before any further load run, or point it at a separate project.

## 7. Catalog search at scale

Local probes on a shared Mac (it was also running Langfuse, Kafka and a k8s node, so absolute numbers are noisy), 50,065 rows: the 65 real products among synthetic near-duplicates, real e5-small embeddings. Details: [catalog research](research/catalog-db.md), section 6. Railway itself was not probed.

- **Latency:** hybrid (FTS + trigram + vector) p50 17 to 34 ms and p95 47 to 105 ms at 50,065 rows. Add the ~80 ms Modal to Railway round trip per catalog query.
- **Filtered HNSW pitfall:** with a selective filter (8.6% of rows) and no iterative scans the vector query returned 0 rows and recall was 0.06; with `relaxed_order` it returned at least 8 of 10 and recall was 0.62.
- **Trigram:** code and typo queries reached hit@5 of 18/18 with it against 13/18 without.
- **The old grader:** `difflib` over the whole 50k catalog took p50 1.5 s, which is why it only grades a pool of 40.
- **Bulk load:** embedding 50k rows took 850 s, the HNSW build 14 s, table and indexes 260 MB.
- **Write path:** about 9 ms to embed plus 7 ms to upsert one product.
- **Past ~1M rows:** `halfvec` to shrink the vectors, BM25 instead of `ts_rank`, then a dedicated search engine. At 100k+ the broad-query tail of the FTS branch (p95 up to ~280 ms alone) is the first thing to fix (AND before OR).

## What was not measured
Skipped by owner decision for budget ($8 of credit, no card): the BF16 baseline on H100, the GPU memory snapshot and the real-model load test. Not re-run after fixes: the H100 FP8 evals. Not recorded: tokens/s on either GPU. Built but not yet measured: `make up PROVIDER=local` on the owner's machine.
