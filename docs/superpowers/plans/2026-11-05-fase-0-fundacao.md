# Phase 0: Repository foundation (implementation plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the `emporio-da-musica-agent` repository with the DDD skeleton of the Python backend and the instructions for coding agents. The quality tools (lint, types, layers, secrets, tests) already run locally and in CI, so phases 2 to 7 only add code.

**Architecture:** Monorepo. This phase contains only `backend/`, an `emporio` package in src layout managed by uv, with the contexts `shared`, `catalog`, `orders`, `policies` and `support`, each with empty `domain/`, `application/` and `infrastructure/` folders. The layers are enforced by import-linter. `AGENTS.md`, `CLAUDE.md` (`@AGENTS.md`) and `.claude/rules` are also added. Secrets are blocked by gitleaks in pre-commit and in CI. `frontend/`, `docker-compose.yml` and `make up` arrive in phases 3 and 5.

**Tech Stack:** Python 3.12, uv, ruff 0.17.3, basedpyright, pytest, import-linter 2.15, pre-commit 4.7 (pre-commit-hooks v6.0.0, ruff-pre-commit v0.17.3, gitleaks v8.30.1), GitHub Actions (setup-uv v10, gitleaks-action v3), GNU Make.

**Spec:** `docs/superpowers/specs/2026-11-05-emporio-agent-design.md`, sections 7.7, 7.9, 7.10, 7.12, 7.13 and 7.14. **Research:** `docs/research/fase-0.md`.

## Global Constraints
- Repo path: repo root (`emporio-da-musica-agent/`).
- Python 3.12, pinned in `backend/.python-version`. The package is called `emporio` and lives in `backend/src/emporio/`.
- Code, identifiers, commits, PRs and all engineering docs (`docs/`, ADRs, `.design/`) in **English**. `README.md`, `examples/` and everything the store's customer reads in **Portuguese** (spec 7.13).
- Conventional Commits with scope, for example `chore(repo): …` or `ci: …`. Subject up to 72 characters, imperative. Every commit ends with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Git flow: initial commit on `main` and the rest of the phase on the `chore/foundation` branch. The PR is opened and the merge only happens after the owner's ok at the checkpoint, with a merge commit and no squash. No force-push.
- No secret enters git: `.env*` is in `.gitignore`, except `.env.example`, which only holds variable names.
- **Do not commit the case statement PDF** (`desafio_tecnico_ai_eng_artefact.pdf`), which is selection-process material. Only the 6 CSVs and `políticas_da_loja.pdf`, which the agent uses, go into `data/`.
- `AGENTS.md` under 200 lines. Rules in `.claude/rules/*.md`, with only `paths:` in the frontmatter.
- GitHub repo **private** until delivery (confirmed on 05/11).

## Review Focus
1. **`.env` with a real key committed by mistake.** Expected: pre-commit (gitleaks) blocks it, and CI fails. Test: Task 4, Step 2.
2. **Name with space and accent in `data/`** (`desafio_tecnico_ai_eng - products.csv`, `políticas_da_loja.pdf`). Expected: the files exist with the exact name and are readable via `pathlib`. Test: `test_case_data_files_are_present` in Task 2.
3. **Outdated `uv.lock`.** Expected: `uv sync --locked` fails in CI instead of installing different versions. Verification: Task 5, Step 3.
4. **Domain importing a framework**, such as `langchain_core` (the root package is different from `langchain`). Expected: `lint-imports` fails. Test: Task 3, Step 2.
5. **Case statement PDF entering the repo through `git add .`.** Expected: `.gitignore` excludes the file. Verification: Task 1, Step 2 (`git status`). It does not become a pytest test, because it is a repository rule and not program behavior.

---

### Task 1: Repository, phase documents and case data

**Files:**
- Create: `.gitignore`, `.env.example`, `README.md` (Portuguese stub: one sentence + "em construção, ver `docs/superpowers/specs/`")
- Create: `docs/superpowers/specs/2026-11-05-emporio-agent-design.md`, `docs/superpowers/plans/2026-11-05-fase-0-fundacao.md` and `docs/research/fase-0.md`, created in this task (approved versions of the spec, the plan and the research)
- Create: `docs/decisions/0001-tools-vs-rag.md`. ADR in English, context, decision and consequences format, about principle 7.1 of the spec: structured data goes to a tool, text goes to RAG.
- Create: `data/` with the 6 quarantine CSVs (original names) and `data/políticas_da_loja.pdf`, copied from `pol_ticas_da_loja.pdf`

**Interfaces:**
- Produces: the `data/` folder, which phases 2 and 3 read by the exact names above.

- [ ] **Step 1:** `mkdir` the repo, `git init -b main`, and copy the docs and the data. `.gitignore` covers `.env`, `.env.*`, `!.env.example`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `node_modules/`, `.superpowers/`, `.design/cache/` and `**/desafio_tecnico_ai_eng_artefact.pdf`. `.env.example` holds only comments with the planned names: `LLM_PROVIDER`, `VLLM_BASE_URL`, `VLLM_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DATABASE_URL`, `DEMO_USER`, `DEMO_PASSWORD`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `STORE_TODAY`.
- [ ] **Step 2:** Run `git status --porcelain`. Expected: no case statement PDF and no `.env` listed.
- [ ] **Step 3: Commit on `main`**
```bash
git add -A && git commit -m "docs(repo): add design spec, phase 0 plan, research and case data"
```
- [ ] **Step 4:** `git switch -c chore/foundation`

### Task 2: `emporio` package with uv and DDD skeleton

**Files:**
- Create: `backend/pyproject.toml` via `uv init --lib --name emporio backend`, `backend/.python-version` (`3.12`), `backend/uv.lock`
- Create: `backend/src/emporio/{shared,catalog,orders,policies,support}/__init__.py`, and in each context except `shared`, `domain/__init__.py`, `application/__init__.py` and `infrastructure/__init__.py`, all empty
- Create: `backend/src/emporio/paths.py`
- Test: `backend/tests/test_paths.py`

**Interfaces:**
- Produces:
  - `emporio.paths.REPO_ROOT: Path` and `emporio.paths.DATA_DIR: Path` (`REPO_ROOT / "data"`);
  - `emporio.paths.CASE_CSV_FILES: dict[str, Path]`, with the keys `products`, `promotions`, `customers`, `categories`, `order_items` and `orders`, pointing to `desafio_tecnico_ai_eng - <key>.csv`;
  - `emporio.paths.POLICIES_PDF: Path` (`DATA_DIR / "políticas_da_loja.pdf"`).
  - Phases 2 and 3 use these names.

- [ ] **Step 1: Write the failing tests**
```python
from emporio import paths

def test_case_data_files_are_present():
    assert set(paths.CASE_CSV_FILES) == {"products", "promotions", "customers", "categories", "order_items", "orders"}
    for f in [*paths.CASE_CSV_FILES.values(), paths.POLICIES_PDF]:
        assert f.is_file() and f.stat().st_size > 0, f
```
The layer structure gets no test of its own: import-linter guarantees the dependencies between layers (Task 3).
- [ ] **Step 2:** `cd backend && uv add --dev pytest ruff basedpyright import-linter pre-commit`, followed by `uv run pytest -q`. Expected: FAIL with `ModuleNotFoundError: emporio.paths`.
- [ ] **Step 3: Implement `emporio/paths.py` and the `__init__.py` files.** `REPO_ROOT` is `Path(__file__).resolve().parents[3]`.
- [ ] **Step 4: Config in `pyproject.toml`.** Whatever a tool can check stays in the tool.
  - `[tool.ruff]` with `line-length = 100` and `target-version = "py312"`.
  - `[tool.ruff.lint] select = ["E","F","I","UP","B","SIM","RUF","ANN","BLE","TRY","DTZ","S","PT","RET","C4","PIE","PERF"]`.
  - `[tool.ruff.lint.per-file-ignores]`: in `"tests/**"`, ignore `["S101","ANN201"]` (assert and unannotated return are accepted in tests).
  - `[tool.basedpyright]` with `typeCheckingMode = "standard"` and `include = ["src","tests"]`, plus `strict = ["src/emporio/*/domain", "src/emporio/*/application", "src/emporio/shared"]`. If the glob in `strict` is not accepted, list the paths of each context.
  - `[tool.pytest.ini_options]` with `testpaths = ["tests"]`.
  - **Proof that the gates bite (red):** a temporary file `src/emporio/shared/_probe.py` with `def f(x): return datetime.now()` must fail in `ruff` (ANN and DTZ) and in `basedpyright` (strict). Then remove the file.
- [ ] **Step 5:** `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run basedpyright`. Expected: all green.
- [ ] **Step 6: Commit** `chore(backend): scaffold emporio package with ddd context layout`

### Task 3: Layer contracts (import-linter)

**Files:**
- Modify: `backend/pyproject.toml` (`[tool.importlinter]` section)

**Interfaces:**
- Produces: the `uv run lint-imports` command, which every phase runs. The contracts apply to the code the phases will create.

- [ ] **Step 1: Write the contracts.**
  - `root_packages = ["emporio"]` and `include_external_packages = true`.
  - **One `layers` contract per context**, listed explicitly because the research does not confirm a wildcard in `containers`. Each with `containers = ["emporio.<ctx>"]` and `layers = ["infrastructure", "application", "domain"]`.
  - **One `forbidden` contract** with:
    - `source_modules = ["emporio.catalog.domain", "emporio.orders.domain", "emporio.policies.domain", "emporio.support.domain", "emporio.shared"]`;
    - `forbidden_modules = ["fastapi", "langchain", "langchain_core", "langgraph", "sqlalchemy", "psycopg", "duckdb", "httpx", "openai", "anthropic", "google"]`.
- [ ] **Step 2: Prove the contract bites (red).** Temporarily create `emporio/catalog/domain/_probe.py` with `import langchain_core`. It may be necessary to install `langchain-core` as a temporary dev dependency only; if it is not installed, use `import fastapi` after a temporary `uv add --dev fastapi`. Run `uv run lint-imports`. Expected: FAIL citing `emporio.catalog.domain._probe`. Then remove the probe and revert the temporary dependency with `git checkout -- backend/pyproject.toml backend/uv.lock` before applying the final config.
- [ ] **Step 3:** `uv run lint-imports`. Expected: `Contracts: N kept, 0 broken.`
- [ ] **Step 4: Commit** `chore(backend): enforce layer and domain-purity contracts with import-linter`

### Task 4: pre-commit with ruff and gitleaks

**Files:**
- Create: `.pre-commit-config.yaml` at the root, with the exact hooks and revs from `docs/research/fase-0.md` §5. The ruff hooks use `args: [--config, backend/pyproject.toml]` and `files: ^backend/`.

- [ ] **Step 1:** `cd backend && uv run pre-commit install --config ../.pre-commit-config.yaml`, followed by `uv run pre-commit run --all-files`. Expected: Passed. Fix whatever the fixers change and run again.
- [ ] **Step 2: Prove that gitleaks blocks (red).** Create `leak_probe.txt` with a fake key in AWS format, assembled at runtime and not written in the plan. Example: `printf 'aws_secret_access_key = %s\n' "$(python3 -c "print('A'*4+'KIA'+'Q'*16)")"`; if that format does not trigger, use another default gitleaks rule. Run `git add leak_probe.txt && git commit -m probe`. Expected: the commit is blocked by the `gitleaks` hook. Then remove the file and run `git reset`.
- [ ] **Step 3: Commit** `chore(repo): add pre-commit with ruff and gitleaks`

### Task 5: CI on GitHub Actions

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Produces:
  - the jobs `backend-quality`, `backend-tests` and `secrets`. Later phases **extend** this file without renaming the jobs:
    - phase 3: Postgres + pgvector service in `backend-tests`;
    - phase 5: `frontend` and `e2e` jobs.
  - Separate, manual workflows in future phases: `evals.yml` (phase 4), `deploy.yml` and `load.yml` (phase 6).

- [ ] **Step 1: Write the workflow.**
  - **Triggers:** `push` and `pull_request`.
  - **Top of the file:** `permissions: contents: read` and `concurrency: {group: ci-${{ github.ref }}, cancel-in-progress: true}`.
  - **`backend-quality`** (`working-directory: backend`, path filter `backend/**` or `.github/workflows/**`): `actions/checkout` and `astral-sh/setup-uv@v10`, pinned by SHA, with the SHA resolved via `gh api repos/astral-sh/setup-uv/git/ref/tags/v10.3.3`. Then run `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run basedpyright` and `uv run lint-imports`.
  - **`backend-tests`:** same setup and same filter, followed by `uv sync --locked` and `uv run pytest -q`.
  - **`secrets`:** `actions/checkout` with `fetch-depth: 0` and `gitleaks/gitleaks-action@v3`, with `GITHUB_TOKEN`. Always runs, with no path filter.
  - **Per-job path filter:** use `dorny/paths-filter`, pinned by SHA, in a `changes` job that the others depend on. `on.paths` would filter the whole workflow, and `secrets` must always run.
- [ ] **Step 2:** Validate the syntax with `uvx check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/ci.yml`. Expected: ok.
- [ ] **Step 3: Prove `--locked` (red).** Run `cd backend && uv add --dev --frozen rich`, which changes `pyproject.toml` without updating the lock, and then `uv sync --locked`. Expected: FAIL. Revert with `git checkout -- pyproject.toml`.
- [ ] **Step 4: Commit** `ci: add parallel backend quality, tests and secret scanning jobs`

### Task 6: AGENTS.md, CLAUDE.md, rules and Makefile

**Files:**
- Create: `AGENTS.md` (English, under 200 lines, sections in the following order):
  - Overview, with 3 lines and a link to the spec;
  - Commands (`make check`, `make test`, `make fmt`);
  - Architecture rules: the dependency table from spec 7.7 and "domain has no IO/frameworks";
  - TDD (red → green → refactor, a pair of `test(x)` and `feat(x)` commits);
  - Commits & PRs: spec 7.10;
  - Secrets: "never write keys; use `.env`, see `.env.example`";
  - Language policy: spec 7.13;
  - Gotchas: the file names in `data/` have spaces and accents, so use `emporio.paths`. Code style: cite `.claude/rules/python-style.md` and say that the ruff and basedpyright strict gates are law. Do not repeat the list in AGENTS.md.
- Create: `CLAUDE.md`, with the single line `@AGENTS.md`.
- Create: `.claude/rules/domain-purity.md` (`paths: ["backend/src/emporio/*/domain/**", "backend/src/emporio/shared/**"]`): pure domain, no IO, with dataclasses and pure functions.
- Create: `.claude/rules/tests.md` (`paths: ["backend/tests/**"]`): test first, one behavior per test, no LLM in unit tests.
- Create: `.claude/rules/secrets.md` (`paths: [".env*", "**/*.yml", "**/*.toml"]`): never real values, only names.
- Create: `.claude/rules/python-style.md` (`paths: ["backend/**/*.py"]`). Only conventions that **no tool checks**, **one line each, no examples, at most ~15 lines in total** (so it does not weigh on the context):
  - money in `Decimal`, never `float`;
  - domain entities as `@dataclass(frozen=True)`, never a loose `dict`;
  - Pydantic only at the edges (API, tools, MCP, config);
  - no `typing.Any`, no `cast`, and `# type: ignore` only with a justification on the same line;
  - own domain exceptions (`OrderNotFound`, `IdentityMismatch`) instead of a generic `ValueError`;
  - functions with an explicit name, one responsibility and no boolean flag that changes behavior;
  - date and time always via `emporio.shared.clock`, never `datetime.now()` directly;
  - `logging` instead of `print`.
  - The rule ends with: "what ruff/basedpyright already block is not repeated here; run `make check`".
- Create: `Makefile` with the `.PHONY` targets:
  - `setup` (`cd backend && uv sync && uv run pre-commit install --config ../.pre-commit-config.yaml`);
  - `fmt`;
  - `lint`;
  - `typecheck`;
  - `imports`;
  - `test`;
  - `check`, which runs lint, typecheck, imports and test.
  - **No `up` in this phase:** it arrives in phases 3 and 5, per YAGNI.
- The skills `adding-agent-tool`, `writing-store-voice` and `running-evals` are left for phase 4, when the flows they describe exist.

- [ ] **Step 1:** `wc -l AGENTS.md`. Expected: under 200. `cat CLAUDE.md`. Expected: exactly `@AGENTS.md`.
- [ ] **Step 2:** `make check`. Expected: all green. `make -n up`. Expected: "No rule to make target" error, confirming the target does not exist yet.
- [ ] **Step 3: Commit** `docs(agents): add AGENTS.md, CLAUDE.md import, path rules and Makefile`

### Task 7: Private GitHub repository and green CI

- [ ] **Step 1:** `gh repo create <owner>/emporio-da-musica-agent --private --source . --remote origin`, followed by `git push -u origin main chore/foundation`.
- [ ] **Step 2:** `gh pr create --base main --head chore/foundation`, with the title `chore: phase 0 foundation`. The body, in English, summarizes the tasks and ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 3:** `gh pr checks --watch`. Expected: `backend-quality`, `backend-tests` and `secrets` pass.

### Task 8: Approval checkpoint (no merge before the ok)
- [ ] **Step 1:** Show the PR link and the repo tree (`tree -L 4 -I '.venv|__pycache__'`), plus the output of `make check` and the three "reds" proven in Tasks 3, 4 and 5.
- [ ] **Step 2:** Ask what changes for phase 1 (Design/GSP). With the ok, run `gh pr merge --merge` (merge commit) and move on to the Phase 1 research.
