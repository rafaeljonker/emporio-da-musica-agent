# Phase 7 (Delivery) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the working system into the deliverable: a complete pt-BR README, ADRs 0002–0010, 3–5 real example conversations from the hosted demo, a clean-clone run that proves the README, final hygiene, and a merged, tagged `v1.0-entrega`.

**Architecture:** Docs only. No code in `backend/src`, `frontend/src`, `deploy/` changes in this phase, except a README gap the clean clone exposes that cannot be fixed in prose (then: stop and ask the owner). Tasks 1 and 2 are independent; Task 3 needs both; Task 4 needs 3; Task 5 needs 4.

**Tech Stack:** Markdown + mermaid, the live API at https://emporio.fastmind.site (httpx + Playwright from `backend/.venv`), git bundle, docker compose, gitleaks.

**Spec:** `docs/superpowers/specs/2026-11-05-emporio-agent-design.md` (§1, §4, §7.1, §7.2.1–7.2.5, §7.7, §7.8, §7.10, §7.11, §7.13, §7.14, §10).

## Global Constraints

- Branch `docs/readme` (from `main` at c6faa51). Never switch, never force-push, never amend, never rewrite history.
- Before every commit: `export PATH="$PWD/backend/.venv/bin:$PATH"` (pre-commit hooks). Trailer on every commit: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Commit scopes: `docs(decisions)`, `docs(examples)`, `docs(readme)`, `docs(repo)`, `docs(spec)`; subject ≤ 72 chars, imperative.
- Language (§7.13): `README.md` and `examples/` in pt-BR; ADRs and every other `docs/**` file in English.
- **Every number has a committed source.** Allowed sources: `backend/evals/reports/{gemini,gemma-h100-fp8,gemma-l40s-fp8}.md`, `docs/scaling-and-cost.md`, `docs/model-selection.md`, `docs/research/*`, the spec. `backend/evals/reports/gemma.md` and `fake.md` are git-ignored: never cite them. A number with no committed source does not go in.
- Hosted demo = Gemini 3.8 Flash (guard on Flash-Lite), owner decision §7.2.5; Gemma 4 31B FP8 on Modal H100 is measured and one flag away (`make deploy-api API_PROVIDER=gemma`). Never claim the demo runs Gemma.
- Honesty rules from `docs/scaling-and-cost.md` carry over verbatim in substance: cold start ≤ 30 s **not met** (~204 s best H100); Gemini p50 7.30 s **misses** the ≤ 3 s target; the H100 report is pre-fix (4 AI tells); the L40S fail is a verifier false negative (22/22 effective); `PROVIDER=local` not measured; real-model load test skipped.
- Public-repo hygiene: no personal names in content (commit authorship may stay), no other projects, no job-search context, no vacancy IDs, no local absolute paths, no credentials. Demo credentials go only by e-mail/Form.
- Agents never do the owner-only steps (end of this plan), never push the tag, never make the repo public, never touch Modal secrets.
- Paid steps (any `make deploy-*`, waking the GPU app, `make evals PROVIDER=gemma`) are out of scope for this phase.

## Review Focus

1. An evaluator on a fresh machine following only the README hits a missing step (Langfuse keys, `make web-keys`, `SESSION_HTTPS_ONLY`, first e5 download ~470 MB, Langfuse image pull ~7 min, Node ≥ 22.12) → Task 4 runs the README literally on a fresh clone and fixes every gap.
2. A README number that drifts from its source (e.g. 22/22 vs 21/22, R$ 0.0307 per case vs per conversation) → Task 3 Step 3 cross-checks every number against the source line.
3. An example showing a wrong fact (price, order date, eligibility) presented as correct → Task 2 Step 4 checks every fact against `data/`.
4. A local absolute path, a personal name or a secret leaking via examples, screenshots or docs → Task 5 grep + gitleaks over full history.
5. The clean clone reusing or clobbering the owner's running stack (same compose project name, ports 5434/3000/8000) → Task 4 Step 1 uses a distinct directory name and stops the main stack first.

---

### Task 1: ADRs 0002–0010

**Files:**
- Create: `docs/decisions/0002-gemma-no-modal.md`, `0003-postgres-pgvector.md`, `0004-embeddings-locais.md`, `0005-canal-simulado.md`, `0006-provedores-por-flag.md`, `0007-langgraph-guard-agent.md`, `0008-gemini-hosted-default.md`, `0009-langfuse-mandatory.md`, `0010-strict-tool-schemas.md`

**Interfaces:**
- Produces: these exact filenames; Task 3's decisions table links each one.

Format: copy `0001-tools-vs-rag.md` (`# NNNN. Title`, `## Context`, `## Decision`, `## Consequences`), English, 10–25 lines each, plus a final `Source:` line naming the spec section / doc it comes from. Filenames 0002–0006 are fixed by the spec §7.7; the slugs stay as listed even though the bodies are English.

Content (decide nothing new; transcribe the recorded decision):
- **0002 Gemma on Modal:** spike result (§ header, `docs/model-selection.md`): Gemma 4 31B 14/14 after prompt v2, best voice; self-hosted open weights on vLLM, H100 FP8 default over L40S (§7.2.5, `docs/scaling-and-cost.md` §1); consequence: ~204 s cold start, so the hosted default moved (→ 0008).
- **0003 Postgres + pgvector:** one Postgres for checkpointer, `turn_metrics`, policy index and Langfuse DB; hybrid retrieval RRF k=5, hit@1/3/5 0.75/0.95/1.00 vs 0.65/0.80/0.90 (§7.2.2); plain SQL migrations.
- **0004 Local embeddings:** fastembed `intfloat/multilingual-e5-small` ONNX, 384 dims, no torch, baked into the API image (image is the pin) (§7.2.2, §7.2.5).
- **0005 Simulated channel:** React web chat simulating WhatsApp (bubbles with `delay_ms`, no token streaming, demo login, identity picked from seed customers, thread id per session) (§7.2.4); the channel port lets WhatsApp be an adapter later.
- **0006 Providers by flag:** `make_chat_model` over `init_chat_model`, `LLM_PROVIDER`/`PROVIDER=gemma|gemini|openai|anthropic|local`, fail early on a missing key, no silent fallback (§7.2.3, §7.14).
- **0007 LangGraph, guard → agent ⇄ tools:** guard every turn with `loja | acessorio | fora_de_escopo | abuso`, `abuso` fixed reply, classifier failure → `loja`; tools called in-process, the same functions exposed over FastMCP (§7.2.3, §7.12).
- **0008 Gemini as hosted default:** owner decision 2026-11-06, $8 Modal credit, ~3.5 min GPU cold start vs 7.30 s p50 that misses ≤ 3 s (`docs/scaling-and-cost.md`).
- **0009 Langfuse mandatory:** startup fails without keys; pseudonymized session ids (HMAC, stable `LANGFUSE_SALT`), name masking before Cloud export (§7.12, §7.2.5).
- **0010 Strict tool schemas:** Pydantic `extra="forbid"`, money as JSON number, numeric strings rejected, validation error returned to the model as a recoverable message (§7.2.5).

- [ ] **Step 1:** Write the nine files.
- [ ] **Step 2:** Verify: `ls docs/decisions | wc -l` → `10`; `grep -L '^## Consequences' docs/decisions/*.md` → empty; every number in them appears in its `Source:` (spot-check each with `grep -F`).
- [ ] **Step 3:** Commit `docs(decisions): add ADRs 0002-0010`.

---

### Task 2: Real example conversations and a chat screenshot

**Files:**
- Create: `examples/01-catalogo-e-preco.md`, `examples/02-promocao-e-parcelamento.md`, `examples/03-arrependimento-cliente-identificado.md`, `examples/04-pedido-anonimo-com-verificacao.md`, `examples/05-acessorio-e-fora-de-escopo.md`, `docs/img/conversa.png`
- Scratch (never committed): `/tmp/emporio-capture/capture.py`, `/tmp/emporio-capture/shot.py`

**Interfaces:**
- Consumes: API contract §7.3.1: `POST /api/auth/login {email,password}`, `GET /api/customers`, `PUT /api/identity {customer_id}`, `POST /api/chat {text}` → SSE `typing`, `bubble {text, delay_ms}`, `metrics {action, ms_model, cost_brl, ...}`, `done {trace_id}`, or `error {partial}`.
- Produces: the five filenames and `docs/img/conversa.png`, linked by Task 3.

Scenarios (pt-BR customer messages, 2–4 turns each, one session per file):
1. Anonymous: asks for violões, then the price of a Takamine and the PIX price.
2. Anonymous: active promotions, then installments on one promoted item.
3. **Identified** (customer 14, as in `backend/evals/agent_cases.toml` `arrependimento_identificado`): wants to return a recent purchase (regret, within the 7-day window per `STORE_TODAY`). Must show `list_my_orders` + `check_return_eligibility`.
4. Anonymous: asks for an order status with a wrong e-mail (rejected without revealing the order exists), then the right one (customer 2, order 8, as in the eval case).
5. Anonymous: an accessory question (guard `acessorio`) and an out-of-scope question (guard `fora_de_escopo`).

- [ ] **Step 1: Capture script** `/tmp/emporio-capture/capture.py`, run with `uv run --project backend python -I /tmp/emporio-capture/capture.py <scenario>`. Reads `DEMO_EMAIL`/`DEMO_PASSWORD` from the repo `.env` with `dotenv_values` (never print, log or write them); `httpx.Client` with cookies against `https://emporio.fastmind.site`; logs in, sets identity, sends each message, parses SSE lines, records per turn: bubbles, `metrics.action`, `metrics.ms_model`, `metrics.cost_brl`. Writes raw JSON to `/tmp/emporio-capture/<scenario>.json`. Space turns ≥ 3 s (rate limit 20 per 600 s per sid).
- [ ] **Step 2: Run** the five scenarios once each. A transport error or `error {partial:false}` may be retried once; a wrong answer is **not** retried silently: stop and report it to the controller (owner decides whether to keep it with a note).
- [ ] **Step 3: Write each `.md`** in this shape (pt-BR):
  ```markdown
  # <título>
  Capturada em 2026-11-0X na demo hospedada (Gemini 3.8 Flash). Identidade: <anônimo | cliente fictício N, nome da base>.
  **Cliente:** <texto>
  **Loja:**
  > <bolha 1>
  > <bolha 2>
  <sub>ferramentas: <action> · <ms_model/1000 com 1 casa> s no servidor · R$ <cost_brl></sub>
  ...
  **Por que é interessante:** 1–2 linhas (qual regra/armadilha a conversa mostra).
  ```
  Bubble text verbatim from the JSON (no edits, no added punctuation).
- [ ] **Step 4: Fact-check** every price, date, order status and eligibility against `data/` (via `emporio.paths`, e.g. a one-off `uv run --project backend python -c` reading the CSVs). Mismatch → stop and report.
- [ ] **Step 5: Screenshot** `/tmp/emporio-capture/shot.py` with Playwright (chromium from `backend/.venv`, viewport 430×900): log in through the UI with the same `.env` values, wait for warm `ready`, send scenario 1's first message, wait for the `done`-state (typing indicator gone), screenshot the chat to `docs/img/conversa.png`. The image must not show the login e-mail; check it with the Read tool before committing.
- [ ] **Step 6: Verify** `grep -rnE 'DEMO_|password|senha|/Users/|/home/' examples docs/img` → no credential or path hits (the word "senha" may only appear inside a customer message, if at all); `ls examples | wc -l` → 5.
- [ ] **Step 7:** Commit `docs(examples): add five real conversations from the hosted demo`.

---

### Task 3: README.md complete (pt-BR)

**Files:**
- Modify (rewrite): `README.md` (keep the current "Como rodar" and "PROVIDER=local" content, it is accurate; restructure around it)

**Interfaces:**
- Consumes: Task 1 ADR filenames, Task 2 example filenames and `docs/img/conversa.png`.

Sections, in this order (§7.8, adjusted to what was built):
1. **Visão geral** (≤ 5 lines): what it is, demo link https://emporio.fastmind.site ("credenciais enviadas por e-mail, fora do repositório"), the screenshot, one line on stack.
2. **Como rodar:** prerequisites (Docker, uv, Node ≥ 22.12, make; ~2.3 GB RAM for Langfuse; first run downloads e5 ~470 MB and Langfuse images ~7 min); `cp .env.example .env`, `make setup`, `make web-keys`, `DEMO_EMAIL`/`DEMO_PASSWORD`; provider choice (`LLM_PROVIDER` + key, or `EMPORIO_FAKE_MODEL=1`); `make up [PROVIDER=gemini|gemma|openai|anthropic|local]`, `make dev`, `make e2e`, `make chat ARGS="--as-customer 14 --provider gemini"`, `make mcp`, `make check`, `make check-web`, `make evals`; the existing `PROVIDER=local` subsection and its table (still "estimativa", not measured).
3. **Arquitetura:** mermaid from spec §7.7 updated: model node = "Gemini 3.8 Flash (demo) · Gemma 4 31B vLLM no Modal · OpenAI/Anthropic/Ollama por flag", add Langfuse and the Cloudflare proxy. Central principle (§7.1): dado estruturado = ferramenta; texto = RAG.
4. **Domínios e organização:** the four domains in one line each and the dependency table from `AGENTS.md` (import-linter enforces it).
5. **Decisões técnicas:** table `decisão | escolha | por quê (1 linha) | ADR`, rows: framework, LLM/provedor, hospedagem da demo, recuperação, embeddings, persistência/histórico, interface, guarda de escopo, schemas das ferramentas, observabilidade, prompt (link to `backend/src/emporio/support/infrastructure/agent/prompts/`). Links to ADRs 0001–0010.
6. **Como escolhi o modelo:** the spike table summary (9 models × 14 scenarios, round 1, prompt v2) + link `docs/model-selection.md`.
7. **Voz humana:** voice guide/persona prompts, bubbles (≤ 3, `delay_ms` rule from §7.3.1, closing period dropped), AI-tell detector and what it flags (`backend/src/emporio/support/domain/ai_tells.py`).
8. **Tratamento de dados e armadilhas:** normalization (accent/plural, difflib), each data trap found and the test that pins it (take them from `docs/research/fase-2.md` and the test names under `backend/tests/unit/`).
9. **Premissas:** `STORE_TODAY`, installments rule, the two phone numbers and the accented e-mail in the PDF (§7.2.2), identity by channel (never by the model), "venda final" on promotion, Campo Grande holiday 08-26 unconfirmed.
10. **Qualidade:** tests (count from `make check` output at the time of writing), CI jobs (`.github/workflows/ci.yml`), evals table per provider with only the three committed reports and their caveats (Global Constraints).
11. **Escala e custo:** 6–10 lines from `docs/scaling-and-cost.md` (GPU choice, cold start not met, load test 120 users 11.2 chats/s 0 failures p50 4.2 s on the fake model, R$ 0.0307 per eval case, ~R$ 0.12 per 4-turn conversation estimate, 1k/10k/100k projection) + link.
12. **Limitações e o que eu faria com mais tempo:** cold start and Gemini latency misses, per-process state (one container), real-model load test, `PROVIDER=local` unmeasured, H100 re-eval after fixes, the parked items of §7.2.4, WhatsApp oficial, handoff humano, reranking, PII guardrails beyond name masking.
13. **Uso de assistentes de IA:** the real flow (brainstorming → spec → research per phase → plan → subagent-driven TDD with red/green commit pairs → multi-lens review via `.claude/skills/reviewing-changes/` → owner checkpoint), `AGENTS.md`/`CLAUDE.md`, `.claude/rules/*`, `.claude/skills/*`, the `Co-Authored-By` trailer; and the owner's calls, each one line, taken from the "Owner decision" entries in §7.2.3–7.2.5 and §7.12 (hybrid retrieval, guard every turn, Langfuse mandatory, bubbles without token streaming, H100 FP8, budget cuts, Gemini hosted, no LLM-as-judge). No personal names.
14. **Exemplos:** links to the five `examples/*.md`, one line each.

- [ ] **Step 1:** Write the README.
- [ ] **Step 2:** Verify links: every relative link resolves — `grep -oE '\]\(([^)#]+)' README.md | sed 's/](//' | grep -v '^http' | xargs -I{} test -e {} || echo MISSING` → no `MISSING`. Mermaid renders (paste into the GitHub preview after Task 5's push, or `npx -y @mermaid-js/mermaid-cli -i` on the block).
- [ ] **Step 3:** Number audit: list every number in the README with its source file and line in the commit body draft; each must `grep -F` in that source.
- [ ] **Step 4:** §7.11 checklist: each row of the statement checklist maps to a README section or file; fix any gap.
- [ ] **Step 5:** Commit `docs(readme): complete README for delivery`.

---

### Task 4: Clean-clone verification

**Files:**
- Modify: `README.md` (only gaps found)

- [ ] **Step 1: Isolate.** In the main checkout: `docker compose --profile observability down` (no `-v`; keeps dev data) and stop any `make up`/`make dev` on :8000. Then `git bundle create /tmp/emporio.bundle docs/readme && git clone -b docs/readme /tmp/emporio.bundle /tmp/emporio-clean/emporio-cleanclone`. The directory name differs from the repo name, so compose uses project `emporio-cleanclone` with fresh volumes (a real first run) and does not touch the owner's volumes; ports are free because the main stack is down.
- [ ] **Step 2: Follow only the README** in the clone, literally, as a new user: `.env` from `.env.example`, `make setup`, `make web-keys`, dummy `DEMO_EMAIL`/`DEMO_PASSWORD`, `EMPORIO_FAKE_MODEL=1`. Run `make check` → green; `make check-web` → green; `make up` → http://localhost:8000 serves login and a fake-model reply (curl login + one chat turn); stop it; `make e2e` → all pass. Record every command the README did not tell you, every wrong expectation and timing.
- [ ] **Step 3:** Fix each gap in the **main** checkout's `README.md` (not the clone). If a gap needs a code/Makefile change, stop and report.
- [ ] **Step 4: Teardown.** In the clone: `docker compose --profile observability down -v` (clone project only). `rm -rf /tmp/emporio-clean /tmp/emporio.bundle`. Restart the main stack only if it was running before (`make db`).
- [ ] **Step 5:** Commit `docs(readme): fix gaps found in a clean clone` (skip if no gaps; report "no gaps" with the command log).

---

### Task 5: Hygiene, PR and review

**Files:**
- Modify: `docs/superpowers/specs/2026-11-05-emporio-agent-design.md` (status line, line 15), `AGENTS.md` (only inaccuracies)

- [ ] **Step 1: Secrets.** `gitleaks git --redact -v .` (full history) → `no leaks found`; `gitleaks dir --redact .` excluding `.env`, `backend/.venv`, `node_modules`, `frontend/dist` → no leaks.
- [ ] **Step 2: Personal traces.** The controller builds a pattern file **outside the repo** (`/tmp/leak-patterns.txt`): the owner's first and last name (from `git config user.name`), names of the owner's other projects (from the controller's memory; never written into the repo), job-search terms (`vaga`, `candidat`, `processo seletivo`, `recrutador`, `entrevista`), `/Users/`, `/home/`. Run `git grep -niIf /tmp/leak-patterns.txt $(git rev-list --all) -- . ':!*.lock' | sort -u` and `git grep -niIf /tmp/leak-patterns.txt` (working tree). Report every hit; fix working-tree hits in docs; history hits are reported to the owner only (no rewrite). Then `rm /tmp/leak-patterns.txt`.
- [ ] **Step 3: Stale content.** Spec line 15 → `> Status: implemented; delivered as tag v1.0-entrega.`; remove the "Em construção" stub (gone with Task 3); `AGENTS.md`: every `make` target listed exists in `Makefile` (`grep -oE '`make [a-z-]+' AGENTS.md | sort -u` vs `grep -E '^[a-z-]+:' Makefile`), line count < 200, mention `examples/` and the ADR folder in one line if absent.
- [ ] **Step 4:** `make check` and `make check-web` green. Commit `docs(repo): final hygiene for delivery`.
- [ ] **Step 5: PR.** `git push -u origin docs/readme`; `gh pr create --base main --title "docs: README, ADRs and examples for delivery"`; body: what changed, numbers' sources, clean-clone log summary, owner-only checklist below; ends with the PR attribution line.
- [ ] **Step 6: Review.** Run `.claude/skills/reviewing-changes/` on the PR (lenses must include L0 and a docs-accuracy lens: numbers vs sources, README runnable). Fix HOLDS findings in new commits; re-run `make check`.
- [ ] **Step 7: Owner checkpoint.** Show the verdict, the rendered README link and the owner-only checklist; wait for the owner's ok.
- [ ] **Step 8: Merge and tag (after the ok).** `gh pr merge --merge` (merge commit, no squash); `git switch main && git pull --ff-only`; `git tag -a v1.0-entrega -m "Delivery" <merge-sha>`. **Push the tag only when the owner says so:** `git push origin v1.0-entrega`.

---

## Owner-only checklist (never done by agents)

- [ ] Rotate the Gemini API key and the Langfuse Cloud keys that appeared in chat.
- [ ] Recreate the Modal secrets `emporio-gemini` and `emporio-langfuse` with the new keys, **keeping the same `LANGFUSE_SALT`** value (pseudonyms depend on it; the one sanctioned exception to the AGENTS.md "never recreate" gotcha, read the old salt first); redeploy `make deploy-api` and send one test message on https://emporio.fastmind.site.
- [ ] Decide how much Modal credit to leave for evaluators (GPU app stays deployed but idle; the demo uses Gemini).
- [ ] Optional: a Langfuse trace screenshot for README §10 (spec §7.12), if wanted.
- [ ] Approve the PR (Task 5 Step 7), then say when to push the tag.
- [ ] Make the repository public at delivery.
- [ ] Reply to the assignment e-mail with the repo link and the demo credentials (`DEMO_EMAIL`/`DEMO_PASSWORD`); fill the Google Form. Target ~20h Mon 2026-11-09, deadline 23:59.
- [ ] After sending: no more changes to the repository.
