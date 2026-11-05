# Lenses

Each lens is a risk question about this product. **Trigger** is the change that makes the lens worth running. **Look at** is where the answer usually lives. **Evidence** is what a claim must cite to count.

## L0 Contract integrity (always)
- **Question:** Does the change do what the phase plan and spec say, nothing missing and nothing extra, and do the docs describe what the code really does?
- **Look at:**
  - the plan tasks against the files changed;
  - claims in AGENTS.md, README, PR body and ADRs against the actual config and code;
  - commit history for TDD pairs (`test(x) … (red)` before `feat(x)`).
- **Evidence:** the plan or spec section quoted next to the diff line or config value that contradicts it.

## L1 Layer and dependency direction
- **Trigger:** anything under `backend/src/emporio/`, or import-linter config.
- **Question:** Can a layer reach something the dependency table in AGENTS.md forbids? This covers domain to IO or frameworks, application to another context's infrastructure, and shared to contexts. Does every rule in the table have a contract that would fail?
- **Look at:** `[tool.importlinter]` and new imports.
- **Evidence:** output of `uv run lint-imports`, or a probe import that the contracts fail to catch.

## L2 Store truth
- **Trigger:** catalog, orders, policies domain or application, tools, or data loading.
- **Question:** Could the agent state a wrong price, stock level, promotion, installment plan, delivery or return window? Cases to check:
  - inactive promotions;
  - `discontinued` or `coming_soon` products, and stock 0;
  - PIX 5% off;
  - installment minimums;
  - 7-day regret window counted from delivery, and 30-day defect window;
  - `STORE_TODAY`;
  - money handled as `float`.
- **Look at:** domain rules and their tests, against `data/` and the policy PDF sections the spec cites.
- **Evidence:** a concrete input row and the wrong output, or a missing test for a rule the spec lists.

## L3 Customer data boundary
- **Trigger:** orders, identity, tools or MCP, API, logging.
- **Question:** Could one customer see another customer's data, or could the model choose whose data it reads? The customer identity must be injected server-side, and the anonymous path needs order number plus email or phone. No PII may appear in logs, traces or errors.
- **Evidence:** a call path where identity comes from model or user input, or a log or trace line carrying PII.

## L4 Agent behavior and voice
- **Trigger:** prompts, graph, guard, tools schema, bubbles, evals.
- **Question:** Will the agent pick the right tool, stay in scope (instruments only, accessories politely declined), and sound human? Signs of sounding like an AI: em dash, markdown, stock phrases, walls of text. Do evals measure each of these, and does the checker accept correct paraphrases?
- **Evidence:** an eval case, a transcript, or a prompt line, with the expected versus the actual behavior.

## L5 Secrets, supply chain and demo access
- **Trigger:** `.env*`, CI, pre-commit, deploy, auth, dependencies.
- **Question:** Can a secret or a demo credential reach git, logs or the client bundle? Are third-party actions and hooks pinned? Do job permissions follow least privilege and still work on PRs? Does the demo login actually protect the paid model endpoint?
- **Evidence:** a file or line, `gitleaks` output, or a workflow line plus the action's documented requirement.

## L6 Run it from a clean clone
- **Trigger:** Makefile, compose, README run steps, CI, paths, packaging.
- **Question:** Do `make check`, `make up` and `make e2e` (when they exist) work for someone who only has the README? Pay attention to path assumptions (`parents[N]`, editable installs), CI filters that skip jobs the tests depend on, and tools that are required but not declared.
- **Evidence:** a command and its output, or a filter or path rule plus the change it fails to cover.

## L7 Cost, latency and scale
- **Trigger:** LLM calls, GPU deploy, caching, load tests, retrieval.
- **Question:** Does the change add model round-trips, tokens, cold-start time or per-request cost without measuring it? Do the numbers in the docs match the measurements?
- **Evidence:** a call count, token or latency figures, or a doc number with no source.

## L8 Frontend and design system
- **Trigger:** `frontend/**`, `.design/**`.
- **Question:** Does the UI use the design tokens, meet WCAG 2.2 AA, show the warm-up state honestly, deliver bubbles in sequence, and keep secrets out of the bundle?
- **Evidence:** component file and line, a contrast ratio, or a screenshot path.
