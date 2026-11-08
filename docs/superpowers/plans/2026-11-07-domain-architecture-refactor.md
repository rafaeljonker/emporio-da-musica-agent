# Domain Architecture Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The owner chose **executing-plans** for this plan.

**Goal:** Restructure backend and frontend around domain-oriented folders, errors as values (Result + domain error codes) with one exhaustive map per boundary, the view-model pattern, and tests that mirror the source by context and layer, without changing any observable behavior.

**Architecture:** The backend keeps its four bounded contexts:
- `domain/` returns `Result` for expected failures.
- `application/` composes them.
- Each boundary translates codes exactly once: `api/errors.py` to HTTP, and `agent/tools/*` to pt-BR text.

Root technical modules move to `emporio/platform/` and composition roots to `emporio/entrypoints/`.

The frontend moves to `src/app` + `src/client/<domain>/{domain,ui,useCases,__tests__}` + `src/client/shared`:
- each use-case component calls one `use{Component}` view model that returns a discriminated union;
- the HTTP client returns `Result<T, ApiError>`;
- `errorMessage.ts` is the only place a code becomes text.

**Tech Stack:** Python 3.12, uv, basedpyright strict, import-linter, pytest + hypothesis. React 19, Vite 8, TypeScript 7, Vitest 5 + jsdom + Testing Library, React Hook Form + zod 4, fast-check, oxlint 1.91.

**Spec:** `docs/superpowers/specs/2026-11-07-domain-architecture-refactor.md`. Inventories: `.superpowers/sdd/2026-11-07-domain-architecture/{backend,frontend}-inventory.md`. The executor reads both inventories; they carry the file:line evidence this plan argues from.

## Global Constraints

- **Refactor only:** same API status codes and bodies, same SSE events, same agent pt-BR texts, same copy, markup, classes and a11y. No new feature.
- **Wire codes stay byte-identical:**
  - catalog: `unknown_category`, `not_found`, `catalog_full`, `catalog_unavailable`, `name_taken_by_store`, `promo_claim`, `too_many_writes`;
  - auth, chat and identity: `too_many_attempts`, `invalid_credentials`, `unauthenticated`, `json_required`, `too_many_messages`, `turn_in_progress`, `too_many_switches`, `unknown_customer`;
  - MCP: `invalid_token`, `too_many_attempts`, `rate_limited`.
- **Tool texts stay byte-identical:** `ORDER_NOT_FOUND`, `ASK_ORDER_IDENTITY`, `ASK_EMAIL_OR_PHONE`, `INSTALLMENTS_NOT_ALLOWED` (+ " O máximo é Nx de R$…"), `INDEX_UNAVAILABLE`, `PRODUCT_NOT_FOUND`, `TOOL_FAILURE`, `CHAT_ERROR`, `ABUSE_REPLY`, `NO_MORE_TOOLS`.
- **e2e selectors depend on visible copy, roles and DOM structure** (frontend inventory §9). No markup, class or copy change during moves.
- **Gates:** `make check` and `make check-web` green on every commit except the red half of a TDD pair. At the end of each slice, also `make test-pg`; after each frontend slice, also `make e2e`. A paid `make evals` only with owner approval; `make evals PROVIDER=gemini` costs ~R$0.65, so ask.
- **TDD:** `test(<ctx>): <behavior> (red)` → `refactor(<ctx>): <behavior>`. A pure move (`git mv` + import fixes) is one `refactor(<ctx>): move …` commit with the gates green, and no red half (nothing new to test).
- **Git:**
  - work on branch `refactor/domain-architecture` from `main`;
  - Conventional Commits, subject ≤ 72 chars, with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`;
  - never force-push, never `--no-verify`, never rewrite `main`;
  - merge commit, and only after owner approval;
  - one PR for the backend (after slice B6) and one for the frontend (after slice F5) are allowed.
- **Python:** no new `Any`, `cast` or `# type: ignore`. `Money` is `Decimal`. Domain entities are frozen dataclasses. Time comes via the clock port.
- **TS:** no `any`, `!` or `as` to silence the compiler.
- **Language:** code, identifiers, commits and docs in English; customer-facing text in pt-BR.
- **Naming:** never name the codebase the patterns were studied from. Before each PR, `git grep -i` for it must return nothing (binary false positives excepted).
- **Dependencies:** the frontend additions are exactly the diff in frontend inventory §5 (react-hook-form 7.91.0, zod 4.6.7, @hookform/resolvers 7.0.3, @testing-library/{dom 10.4.2, jest-dom 7.0.1, react 16.3.3, user-event 14.6.8}, fast-check 4.10.2, jsdom 31.0.0). No backend dependency is added; hypothesis is already in the dev group.

## Lean test budget (owner decision, overrides the per-task test lists below)

- **Backend, about +10 net.**
  - Existing `pytest.raises(...)` tests are rewritten to assert `Err(...)`; they are not duplicated.
  - New tests only for: map exhaustiveness (HTTP and tool text), `test_result.py`, the generic 500, data error → `TOOL_FAILURE`, and `secret_text`.
- **Frontend, about +35.**
  - `renderHook` tests only for hooks with real behavior: `useQueuedMessage`, `useWarmStatus`, `useChatStream`, `useProductForm`, `useCatalogDialog`, `useApp` (session expiry). Each covers its states and transitions, with no per-render tests.
  - **No component tests:** the e2e covers rendering and its selectors pin the markup.
  - **fast-check** only for the pacing and queue invariants.
  - **`errorMessage`:** one parametrized test, one row per code.
  - The `api.test.ts` cases of F1 stay.
- **Existing tests are not deleted** in this refactor, only moved or reshaped.

## Owner decisions this plan assumes (confirm at review)

- **D1. Result stops at the tool boundary.** LangGraph ToolNode, the SSE route and the MCP wrappers keep their current shapes:
  - each tool function matches the use case's `Result` and returns the same pt-BR text;
  - the turn (`runner.py`), the guard and the SSE route keep catching unexpected exceptions as today;
  - `HandleMessage -> Reply(failed=...)` stays.
  - Reason: ToolNode and SSE need a string or an exception, and the MCP contract pins texts (backend inventory §9).
- **D2. Validation stays outside Result.** Pydantic argument validation (`_StrictTool`, `_retry_hint`) and FastAPI 422 lists remain a third channel.
- **D3. Constructors keep raising.** `Money` and `Settings` cannot return Result; their invariants keep raising, and the edges already validate first.
- **D4. Catalog form validation stays on submit.** `mode: 'onSubmit'`, `reValidateMode: 'onSubmit'`, `shouldFocusError: false`. Today's UX; on-touch would change behavior.
- **D5. TS Result shape** is `{ ok: true; data: T } | { ok: false; error: E }`, as in the spec.
- **D6. Session expiry becomes one listener.** A module-level `notifySessionExpired()` replaces the 9 `instanceof SessionExpired` checks and the `onExpired` prop drilling. Same behavior, one place.
- **D7. Cut line if time runs short before Monday 20:00:**
  - ship the backend PR (slices B0-B6) plus frontend slices F0-F2;
  - leave F3-F5 on the branch, with the README "with more time" line updated;
  - every slice leaves the app working, so any prefix is shippable.

## Review Focus

- **401 from a non-login route mid-action** (catalog save, chat send, identity switch). Expected: sign-out with the "sessão expirou" copy, and the queued message is kept. Pinned in F1 (`api.test.ts: notifies session expiry once per 401`) and F2 (`useQueuedMessage keeps text on unauthenticated`).
- **Proxy 503 with no JSON `detail`.** Expected: catalog shows "unavailable" copy, not "failed". Pinned in F1 (`errorMessage: status 503 without code reads unavailable`).
- **Unexpected exception inside a catalog route** (e.g., a bug in a mapper). Expected: generic 500 body, no stack or message, server-side log. Pinned in B5 (`test_unexpected_error_returns_generic_500_without_message`).
- **DB down during an agent tool call vs a CSV/config error.** Expected:
  - DB down still gives `INDEX_UNAVAILABLE`;
  - a CSV or config error is now a `ToolCrashed` (logged as a type) and no longer "Dado inválido.".

  This is the one deliberate correction; the agent text for a bug becomes `TOOL_FAILURE`. Pinned in B4 (`test_store_unavailable_is_index_unavailable`, `test_data_error_is_tool_failure_not_invalid_data`). **This changes one agent text for an internal-bug path. Owner confirms at review.**
- **"Editar" clicked twice on the same product after typing.** Expected: the form resets to the stored product. Pinned in F4 (`useProductForm: editing the same product again resets typed values`).

---

## Backend

### Task B0: Branch, baseline and repo hygiene

**Files:**
- Modify: `docs/superpowers/specs/2026-11-05-emporio-agent-design.md` (remove the hiring-stage sentence)
- Untrack: `.design/projects/*/design/shared/personas.md`, `.design/projects/*/critique/`, `.design/CLAUDE.md`
- Rename ADRs and research docs to English:
  - `0002-gemma-no-modal.md` → `0002-gemma-on-modal.md`
  - `0004-embeddings-locais.md` → `0004-local-embeddings.md`
  - `0005-canal-simulado.md` → `0005-simulated-channel.md`
  - `0006-provedores-por-flag.md` → `0006-provider-by-flag.md`
  - `docs/research/fase-N.md` → `docs/research/phase-N.md`
  - `catalog-db.md` keeps its name
- Modify: every link to these files (`git grep -n "decisions/000\|research/fase"`), in both READMEs, ADRs, AGENTS.md, the spec and the plans.
- Create: `backend/README.md` (5 lines: layout, `make check`, pointer to the root READMEs).

- [ ] Step 1: `git checkout main && git pull && git checkout -b refactor/domain-architecture`. Record baseline counts: `make check` (expected 823 passed, 50 skipped), `make check-web` (66), `make test-pg`.
- [ ] Step 2: Do the renames with `git mv`. Fix the links. Untrack with `git rm --cached -r` and add those paths to `.gitignore`. Grep the spec for "stage", "hiring" and "processo" and remove the hiring-process text.
- [ ] Step 3: Check that `git grep -nE "fase-[0-9]|embeddings-locais|canal-simulado|provedores-por-flag|gemma-no-modal"` returns only history-free hits (none), and that `make check` is green.
- [ ] Step 4: Commit `docs(repo): English doc names, drop hiring-process notes`.

### Task B1: `shared/result.py`, plus catalog errors as values

**Files:**
- Create: `backend/src/emporio/shared/result.py`, `backend/tests/shared/test_result.py`
- Modify: `catalog/domain/errors.py` (replace the exception classes with an enum), `catalog/domain/installments.py`, `catalog/application/{get_product,quote_installments,create_product,update_product}.py`
- Move: `support/application/ports.py:73-126` (ProductInput, ProductView, CatalogAdmin) and `support/infrastructure/catalog_admin.py` → `catalog/application/admin.py` (DTOs, the `CatalogAdmin` protocol and the service class `CatalogAdminService`). Delete `CatalogWriteRejected` and `RejectionCode`.
- Modify: `shared/errors.py` gains `class StoreUnavailable(Exception)`; `db.py`'s `IndexUnavailable` is replaced by it, re-raised from the Pg adapters.
- Modify: `pyproject.toml`:
  - basedpyright `reportMatchNotExhaustive = "error"`;
  - import-linter: drop the two catalog_admin ignores, and let `api` import `emporio.catalog.application.admin`.

**Interfaces:**
- Produces:
  - `Ok[T](value: T)` and `Err[E](error: E)`, frozen dataclasses, with `type Result[T, E] = Ok[T] | Err[E]`;
  - `CatalogErrorCode(StrEnum)`: `PRODUCT_NOT_FOUND="product_not_found"`, `UNKNOWN_CATEGORY="unknown_category"`, `PRODUCT_NOT_OWNED="not_found"`, `CATALOG_FULL="catalog_full"`, `NAME_TAKEN_BY_STORE="name_taken_by_store"`, `PROMO_CLAIM="promo_claim"`, `INSTALLMENTS_NOT_ALLOWED="installments_not_allowed"`, `CATALOG_UNAVAILABLE="catalog_unavailable"`.
  - New signatures:
    - `installment_plan(total: Money, count: int | None) -> Result[InstallmentPlan, CatalogErrorCode]`
    - `minimum_for(count: int) -> Money | None`
    - `GetProduct.__call__(product_id: int) -> Result[tuple[Product, PriceQuote], CatalogErrorCode]`
    - `QuoteInstallments.__call__(total: Money, count: int | None) -> Result[InstallmentPlan, CatalogErrorCode]`
    - `check_draft(repo, writer, draft) -> CatalogErrorCode | None`
    - `CreateProduct.__call__(owner: str, draft: ProductDraft) -> Result[Product, CatalogErrorCode]`
    - `UpdateProduct.__call__(owner: str, product_id: int, draft: ProductDraft) -> Result[Product, CatalogErrorCode]`
    - `CatalogAdmin.create/update -> Result[ProductView, CatalogErrorCode]`; `categories()` and `mine()` return `Result[..., CatalogErrorCode]`, with `CATALOG_UNAVAILABLE` when `StoreUnavailable` is caught.
  - `StoreUnavailable(Exception)` in `emporio.shared.errors`.

- [ ] Step 1: Red tests (each file one behavior per test):
  - `tests/shared/test_result.py`: `test_ok_and_err_are_frozen`, `test_match_narrows_ok_and_err`.
  - `catalog/domain`: `test_installment_plan_past_twelve_is_err_installments_not_allowed`, `test_minimum_for_past_twelve_is_none`, `test_installment_plan_property_parcel_times_count_covers_total` (hypothesis, `@settings(derandomize=True)`).
  - `catalog/application`:
    - `test_get_product_unknown_id_is_err_product_not_found`;
    - `test_create_product_*` for each Err: unknown category, promo claim, name taken by store, catalog full;
    - `test_update_product_foreign_owner_is_err_product_not_owned`;
    - one `Ok` test per use case;
    - `test_admin_categories_db_down_is_err_catalog_unavailable`.
  - Put these in the current test files. The move happens in B6.
- [ ] Step 2: `make test`. Expect failures that name the missing `Result` / `CatalogErrorCode`. Commit `test(catalog): expected failures return Result (red)`.
- [ ] Step 3: Implement. Domain and application code has no `try/except`. Only `CatalogAdminService` catches `StoreUnavailable`. Update the callers: tools.py:218,237 (temporarily `match` and return the same texts), `api/catalog.py:96-141` (temporarily map `Err.error.value` to the existing `_STATUS`), `tests/fakes/fake_catalog_admin.py`.
- [ ] Step 4: `make check` green, plus `make test-pg`. Commit `refactor(catalog): expected failures return Result`.

### Task B2: orders errors as values

**Files:** `orders/domain/errors.py` (enum), `orders/domain/identity.py`, `orders/application/{get_order_status,check_return_eligibility}.py`, tools.py:262-279.

**Interfaces:**
- Produces:
  - `OrdersErrorCode(StrEnum)`: `ORDER_NOT_FOUND="order_not_found"`, the one code for an unknown order, a foreign order or an identity mismatch (anti-enumeration);
  - `GetOrderStatus.__call__(order_id: int, email_or_phone: str) -> Result[Order, OrdersErrorCode]`;
  - `CheckReturnEligibility.__call__(order_id: int, customer_id: int) -> Result[ReturnEligibility, OrdersErrorCode]`.
  - Delete `OrderNotFound` and `IdentityMismatch`.

- [ ] Step 1: Red tests:
  - `test_get_order_status_wrong_email_is_err_order_not_found`;
  - `test_get_order_status_unknown_order_is_err_order_not_found`;
  - `test_check_return_eligibility_foreign_order_is_err_order_not_found`;
  - the Ok cases (order 7 eligible, order 5 not, order 17 cancelled not eligible).
  - Commit the red half.
- [ ] Step 2: Implement. `check_return_eligibility` in tools does a `match` with early return (no bind helper). Gates green, then commit `refactor(orders): expected failures return Result`.

### Task B3: policies purity and the clock

**Files:** move `shared/clock.py SystemClock` → `platform/clock.py` (keep the `Clock` Protocol in `shared/clock.py`). `NaiveDatetimeError` and `NoOpeningFound` stay as plain `Exception` (UNEXPECTED), no longer `DomainError`. `EmptyPolicySource` stays raised.

- [ ] Step 1: Red: `test_store_hours_naive_datetime_raises_plain_exception_not_domain_error`. Commit the red half.
- [ ] Step 2: Implement, fix the importers, and green. Commit `refactor(policies): unexpected failures are plain exceptions`.

### Task B4: support: split the tools package, one code→text map, unexpected → ToolCrashed

**Files:**
- Split `support/infrastructure/agent/tools.py` into `agent/tools/{__init__,base,catalog,orders,policies}.py`, following backend inventory §7.
- `__init__` exports `Toolbox`, `build_tools` and `PLAIN` (the tuple MCP uses).
- `catalog.py` holds `CATALOG_TEXT: dict[CatalogErrorCode, str]`. `orders.py` holds `ORDERS_TEXT: dict[OrdersErrorCode, str]`. A code missing from either map fails at import (see the test).
- `base._safe` catches only `StoreUnavailable` → `INDEX_UNAVAILABLE`, and `Exception` → `ToolCrashed`, logging the type name only. The `except DomainError` branch and the "Dado inválido." literal are deleted. The dead "O valor precisa ser maior que zero." literal is deleted too.
- Move `TurnProbe` → `agent/turn_probe.py`, and the cost math → `agent/cost.py` (a pure function).
- Update `mcp/server.py` to `tools.PLAIN`. Rename the import-linter ignores to `...agent.tools.catalog -> emporio.catalog.*` (likewise orders and policies). Delete `DomainError` once nothing inherits from it.

- [ ] Step 1: Red tests:
  - `test_every_catalog_code_has_tool_text` and `test_every_orders_code_has_tool_text`: iterate the enum and assert the maps' key sets are equal;
  - `test_store_unavailable_is_index_unavailable`;
  - `test_data_error_is_tool_failure_not_invalid_data`;
  - `test_tool_texts_unchanged`: snapshot of all constants, including `INSTALLMENTS_NOT_ALLOWED + " O máximo é 12x de R$ 100,00"` for a R$ 1.200 total with 13x.

  Commit the red half.
- [ ] Step 2: Implement the split as `git mv tools.py tools/catalog.py`, then extract the other modules, so history follows. Gates green: the contract snapshots in `test_tool_schemas` and `test_mcp_contract` must not change. Commit `refactor(support): tools per context with one code-to-text map`.

### Task B5: api: exhaustive error maps, masked unexpected errors

**Files:**
- Create `api/errors.py` with:
  - `ApiErrorCode(StrEnum)`, holding the 11 API-only codes of backend inventory §2;
  - `CATALOG_HTTP: dict[CatalogErrorCode, int]`;
  - `API_HTTP: dict[ApiErrorCode, int]`;
  - `def error_response(code: StrEnum, status: int) -> JSONResponse` returning `{"detail": code.value}`;
  - a global handler `unexpected_error(request, exc) -> JSONResponse`: 500 `{"detail": "internal_error"}`, which logs `logger.exception` server-side.
- Modify `api/{auth,chat,catalog,identity,guards,mcp_auth}.py` to raise or return through these maps; no string literals for codes remain.
- `app.py` registers the handler.
- The pt-BR message part of the spec's `(status, message)` lives in the frontend `errorMessage.ts` (F1), because the API sends codes only, and that must stay byte-identical.

**Interfaces:**
- Produces `CATALOG_HTTP`, `API_HTTP`, `ApiErrorCode`, `unexpected_error`.
- The 500 body changes from Starlette's plain text "Internal Server Error" to JSON `{"detail":"internal_error"}`. **This is a wire change on a path that is a bug today; the owner confirms at review.** The alternative is to keep a plain-text 500 through `PlainTextResponse("Internal Server Error", 500)`.

- [ ] Step 1: Red tests in `tests/unit/api/test_errors.py`:
  - `test_every_catalog_code_has_http_status`;
  - `test_every_api_code_has_http_status`;
  - `test_catalog_wire_codes_unchanged` (parametrized: code → (status, detail), from today's `_STATUS`);
  - `test_unexpected_error_returns_generic_500_without_message`: a route that raises `RuntimeError("secret-xyz")`; the body excludes "secret-xyz" and "Traceback", and the log has it.

  Commit the red half.
- [ ] Step 2: Implement. Each `match` on a code ends with `case _: assert_never(code)`. Gates green, plus the existing `test_catalog.py:173-263` unchanged. Commit `refactor(api): exhaustive error maps, generic 500`.

### Task B6: platform/entrypoints, config split, state doc, tests mirror the source

**Files:**
- `git mv` the root modules to `emporio/platform/{config/,db.py,embeddings.py,migrate.py,paths.py,local_model.py,clock.py}` and `emporio/entrypoints/{bootstrap,web,cli,ingest}.py`.
- Split `config.py` into `platform/config/{settings,checks,mcp_tokens,errors}.py`. Config errors become plain `Exception`.
- One `secret_text(value: SecretStr | None) -> str` in `platform/config/settings.py` replaces the 7 copies.
- Fix `paths.py REPO_ROOT = parents[4]`.
- Update the Makefile (`-m emporio.platform.migrate`, `-m emporio.entrypoints.ingest`, `--factory emporio.entrypoints.web:create_web_app`) and pyproject `[project.scripts] emporio = "emporio.entrypoints.cli:main"`.
- Update the import-linter module names and add the contract that `emporio.platform` never imports a context. Close the api loophole: the "API stays on the application layer" contract also forbids `emporio.{catalog,orders,policies}.domain` (except the enums `*.domain.errors`, allowed by an explicit `ignore_imports` line) and `emporio.{orders,policies}.application`. Remove `config`'s import of `support.application.warmup`: `fake_warm_mode` becomes a `Literal` string.
- Update the ruff per-file ignore, `e2e/conftest.py` and `deploy/modal_api.py` (imports, module list, and the bake copies `platform/__init__.py` plus `platform/embeddings.py`).
- Create `docs/architecture/state.md` (≤ 40 lines, from backend inventory §5). No behavior change.
- Tests:
  - `git mv` every test to the layout of backend inventory §8;
  - shared builders go to `tests/<ctx>/fakes.py` (`make_box` → `tests/support/fakes.py`) and `tests/api/helpers.py`;
  - add markers `files` and `contract`, plus `--strict-markers`;
  - `git grep "from tests.unit"` returns nothing.

- [ ] Step 1: Pure moves in three commits, each with the gates green:
  1. `refactor(platform): move technical modules to emporio/platform`;
  2. `refactor(entrypoints): move composition roots`;
  3. `refactor(tests): mirror the source by context and layer`.

  After each: `make check`, `make test-pg`, and `make e2e` (it boots `emporio.entrypoints.web`).
- [ ] Step 2: Red `test_secret_text_unwraps_and_defaults_empty`, then implement and remove the copies. Commit both halves.
- [ ] Step 3: Deploy smoke without deploying: `cd backend && uv run python -c "import deploy.modal_api"` (or the existing `test_deploy_config.py`) passes, and `uv run modal run deploy/modal_api.py::bake_e5 --help` resolves the paths. The real `make deploy-api` waits for the owner.
- [ ] Step 4: Docs:
  - AGENTS.md: folder map, layer table (platform, entrypoints), Result/error-code rules, test layout;
  - `.claude/rules/backend-errors.md` with `paths: backend/src/**`: Result for expected failures, an enum per context, a map per boundary, `assert_never`, no message parsing;
  - ADRs `0013-domain-errors-as-values.md` and `0014-error-mapping-at-the-boundaries.md`, each ≤ 25 lines: context, decision, consequences, alternatives.

  Commit `docs(architecture): result, error codes and layout`.
- [ ] Step 5: Run `git grep -i` for the reference name (nothing). Open the backend PR `refactor(backend): domain errors as values and platform layout` and **stop for owner approval**.

## Frontend

### Task F0: Move to the domain layout, test setup, lint fences

**Files:**
- `git mv` per the frontend inventory §2 table: `src/app/*`; `src/client/{auth,catalog,chat,warmup}/…`; `src/client/shared/{components/ui,lib}/…`.
- Keep `copy.ts` as `src/client/shared/lib/copy.ts`.
- Update the `@/` aliases, `components.json` and `index.css` path.
- Rename `useQueuedMessage.tsx` and `useWarmStatus.tsx` to `.ts`.
- Install the deps of the inventory §5 diff (show the `package.json` diff to the owner in the step's output before `npm install`).
- `vite.config.ts` gets `test: { environment: 'jsdom', setupFiles: ['./src/test-support/setup.ts'], restoreMocks: true, unstubGlobals: true }`.
- Create `src/test-support/{setup,fixtures,sse}.ts` per inventory §6.
- `.oxlintrc.json` gets the two overrides of inventory §7, and moves the `components/ui` override path.
- Move the existing tests to `__tests__/` without changing their content.

- [ ] Step 1: The moves in one commit, `refactor(web): domain folder layout`. Then `make check-web` and `make e2e` must be green, with the same 66 tests.
- [ ] Step 2: Deps, config and setup in one commit, `chore(web): jsdom, testing-library, rhf, zod, fast-check`. Prove the lint fences with one throwaway violation per rule (do not commit it).
- [ ] Step 3: Create `src/shared/result.ts` with `type Result<T, E> = { ok: true; data: T } | { ok: false; error: E }` and the `ok()` / `err()` builders.

### Task F1: HTTP client returns Result, `errorMessage`, session-expiry listener

**Files:** `src/client/shared/lib/{api.ts,apiTypes.ts,errorMessage.ts,session.ts,focus.ts}`, plus `__tests__`.

**Interfaces:**
- Produces:
  - `ApiErrorCode` as the 17-member union of inventory §4 (15 backend codes, plus `invalid_fields`, `network` and `unknown`);
  - `interface ApiError { code: ApiErrorCode; status: number | null }`;
  - every endpoint function returns `Promise<Result<T, ApiError>>`; `streamChat` returns `Promise<Result<void, ApiError>>` and keeps its event callback;
  - `notifySessionExpired()` and `onSessionExpired(listener) -> unsubscribe`;
  - `errorMessage(error: ApiError, context: 'login' | 'catalogLoad' | 'catalogSave') -> string`;
  - `fieldFor(code) -> 'categoryId' | 'name' | null`;
  - `focusById(id)` and `isFinePointer()`.

- [ ] Step 1: Red tests:
  - `api.test.ts` (fetch stubbed with `sse.ts` and plain JSON responses): `maps detail string to code`, `maps 422 detail list to invalid_fields`, `network TypeError is network with null status`, `notifies session expiry once per 401 except login`, `login 401 is invalid_credentials without notifying`;
  - `errorMessage.test.ts`: one test per row of inventory §4, including `status 503 without code reads unavailable` and `too_many_attempts on login reads network copy`;
  - move the `errorCopy` cases from `form.test.ts` here, unchanged.

  Commit the red half.
- [ ] Step 2: Implement. Callers temporarily adapt in place: they unwrap Result and keep today's behavior. Then `make check-web` and `make e2e`. Commit `refactor(web): http client returns Result, one error message map`.

### Task F2: warmup view models

**Files:**
- `warmup/useCases/warmupStatus/{WarmupStatus.tsx,useWarmupStatus.ts,useWarmStatus.ts}`;
- `warmup/useCases/queuedMessage/useQueuedMessage.ts`;
- `warmup/ui/{StatusRegion,PegsDrawing}.tsx`;
- `warmup/domain/{format,queue}.ts`.

**Interfaces:**
- `useWarmStatus(seed, enabled) → checking | polling{status, elapsed, networkError} | ready{status} | failed{status}`.
- `useWarmupStatus(props) → checking | waiting | long | ready | failed`, with `networkError` and handlers. The `lastStage` and `longSaid` refs become `announced` state, and `announce` is read through `useEffectEvent`.
- `useQueuedMessage(ready) → empty | queued{lines} | flushed`. The `flushed` ref becomes state.

- [ ] Step 1: Red `renderHook` tests, the list of inventory §6 for these three hooks, with fake timers.
  - Component tests: `WarmupStatus` renders each state, with `useWarmupStatus` mocked.
  - fast-check properties for the queue: enqueue null beyond 1000, undo round-trip, load/save round-trip, with `fc.configureGlobal({ seed: 42 })`.
  - Commit the red half.
- [ ] Step 2: Implement. Gates green, plus `make e2e` (in particular `test_queued_message_sent_once_when_ready`). Commit.

### Task F3: auth and app view models

**Files:** `src/app/{App.tsx,useApp.ts}`, `auth/useCases/session/useMe.ts`, `auth/useCases/login/{LoginScreen.tsx,useLoginScreen.ts,useWarmExpected.ts}`.

**Interfaces:**
- `useApp() → checking | signedOut{expired} | signedIn{warm, fromLogin, customerId}`, subscribing to `onSessionExpired`.
- `useLoginScreen() → idle | submitting | error{reason: 'empty' | 'invalid' | 'network' | 'expired'}`.
- Login stays plain view-model state; the owner may ask for RHF.

- [ ] Step 1: Red `renderHook` tests (inventory §6: useApp ×3, useLoginScreen ×5) and the component tests for each state. Commit the red half.
- [ ] Step 2: Implement, remove the `onExpired` drilling, then gates and e2e. Commit.

### Task F4: catalog: view models and RHF + zod

**Files:**
- `catalog/domain/{form.ts (productSchema),catalog.ts}`;
- `catalog/useCases/catalogDialog/{CatalogDialog.tsx,useCatalogDialog.ts,useCategories.ts,useMyProducts.ts}`;
- `catalog/useCases/productForm/{ProductForm.tsx,useProductForm.ts}`;
- `catalog/ui/{Field,MyProducts,SavedPanel}.tsx`.

Reuse from branch `refactor/catalog-view-model`:
- `ui/*` markup;
- `domain/catalog.ts` and its test;
- `focusField`;
- the `opening`/`load` counters and the saved-row merge.

Drop its `domain/use*` hooks and its `useProductForm`.

**Interfaces:**
- `productSchema` (zod) with `z.input` → `ProductBody`. The messages are byte-identical to `copy.catalog.errors`, and the field rules are those of inventory §5.
- `useCategories()` and `useMyProducts(enabled)` → `pending | error{error: ApiError} | success{data}`.
- `useCatalogDialog() → { panel: form{editing} | saved{name, edited}; mine: pending | ready{products}; open; alert; categories; handlers }`.
- `useProductForm({ editing, onSaved }) → editing | saving`, plus RHF `formState`:
  - `useForm({ resolver: zodResolver(productSchema), mode: 'onSubmit', reValidateMode: 'onSubmit', shouldFocusError: false, defaultValues: EMPTY, values })`;
  - server errors go through `setError(fieldFor(code) ?? 'root.server')`;
  - remount uses `key={formKey}`.

- [ ] Step 1: Red tests:
  - the `form.test.ts` validation cases rerun through `productSchema.safeParse`, with identical messages;
  - fast-check `toPrice(priceInput(d)) === d` and `mergeById` (no duplicates, local order kept);
  - `renderHook` tests of inventory §6 for useCatalogDialog and useProductForm, including `editing the same product again resets typed values`, `name_taken_by_store focuses name`, `promo_claim shows root alert`;
  - component tests per state with the view model mocked.

  Commit the red half.
- [ ] Step 2: Implement. Gates green, plus the 3 catalog e2e tests. Commit `refactor(catalog): view models and schema-owned form`.

### Task F5: chat view models (last)

**Files:**
- `chat/domain/{entries,composer,metrics,pacing,turn}.ts`;
- `chat/useCases/chatShell/{ChatShell.tsx,useChatShell.ts,useChatStream.ts,useReadyHandoff.ts}`;
- `chat/useCases/transcript/{Transcript.tsx,useTranscript.ts}`;
- `chat/useCases/metricsDetails/{MetricsDetails.tsx,useMetricsDetails.ts}`;
- `chat/useCases/demoStrip/{DemoStrip.tsx,useDemoStrip.ts,useCustomers.ts}`;
- `chat/ui/{Composer,EmptyState,TypingIndicator}.tsx`.

**Interfaces:**
- `useChatShell() → warming{warmup, compact, onSend} | chat{localNotice, showEmpty, onSend}`, with base `{entries, typing, busy, text, setText, said, handlers}`.
- `useTranscript() → following | unseen`.
- `useMetricsDetails() → closed | open`, with `last: none | some`.
- `useDemoStrip() → customers: loading | failed | ready{list}`.
- `applyEvent(entries, event) → entries`, a pure function in `chat/domain/entries.ts`.
- `createPacer` moves byte-identical.

- [ ] Step 1: Red tests:
  - `applyEvent` unit tests;
  - fast-check pacing properties (inventory §6: order, terminal last at most once, nothing after abort, total time = Σ delay);
  - the `renderHook` list for useChatStream, useChatShell, useTranscript, useMetricsDetails and useDemoStrip;
  - component tests per state.

  Commit the red half.
- [ ] Step 2: Implement, then gates and the full `make e2e`. Commit.
- [ ] Step 3: Docs:
  - AGENTS.md frontend map and the view-model rules;
  - `.claude/rules/frontend-view-models.md` with `paths: frontend/src/**`;
  - ADR `0015-frontend-domain-folders-and-view-models.md` (≤ 25 lines).
- [ ] Step 4: Final checks:
  - all gates: `make check`, `make check-web`, `make test-pg` and `make e2e`;
  - `git grep -i` for the reference name returns nothing;
  - a whole-diff review with `superpowers:requesting-code-review` on the most capable model;
  - fix its FIX-NOW findings, then open the frontend PR and **stop for owner approval**.

## After both PRs merge (owner-gated)

- `make deploy-api` (the paths moved, so this is a real check of the Modal image); then a smoke test of login, chat, catalog and `/mcp` on emporio.fastmind.site.
- Regenerate the delivery PDF (README + docs), and update the README test counts.
