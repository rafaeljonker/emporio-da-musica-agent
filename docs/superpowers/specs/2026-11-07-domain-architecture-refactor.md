# Domain architecture refactor: domain folders, view models, errors as values, layered tests

Owner brief, 2026-11-07. A refactor: behavior, API contract, agent speech, pt-BR copy, design system and accessibility stay identical. No new feature.

## A. Backend (Python)
1. **Pure domain.** Each context keeps `domain/` (entities, value objects, pure rules, no IO or framework), `application/` (one use case per file, domain plus ports) and `infrastructure/` (adapters). Fix any IO or framework that leaked into `domain/`. Keep the import-linter contracts and tighten them where loopholes exist.
2. **Expected errors as values.**
   - `shared/result.py` defines `Ok[T]` and `Err[E]` (frozen dataclasses) and `Result = Ok[T] | Err[E]`.
   - Each context has a `StrEnum` of codes in `domain/errors.py`.
   - Use cases and rules that raise for expected failures return `Result` instead.
   - Exceptions stay for the unexpected (bugs, infrastructure down).
   - basedpyright strict forces callers to handle `Err`.
3. **One exhaustive map per boundary.**
   - **`api/`:** one `dict[ErrorCode, (HTTP status, pt-BR message)]` per context, with a test that every enum member is mapped, and `assert_never` in `match` statements.
   - **Agent tools:** one code-to-text translation.
   - No layer parses an error message to decide anything.
4. **Unexpected errors masked and logged.** The API never returns a stack trace or an internal message. The server logs the error, and the client gets a generic message.
5. **State.** Document where each piece of backend state lives (per-process memory, Postgres, the LangGraph checkpointer, the session), in one place. No behavior change.
6. **Types.** Keep basedpyright strict where it is today. No new `Any`, `cast` or `# type: ignore`.

## B. Frontend (React)
1. **Domain folders.**
   - `src/app/` holds bootstrap.
   - `src/client/<domain>/{domain,ui,useCases/<case>/,__tests__}` for chat, catalog, auth and warmup:
     - `domain/` holds pure client rules: no React, no IO;
     - `ui/` holds presentation components with no hooks and typed props;
     - `useCases/<case>/` keeps `Component.tsx` and `use{Component}.ts` together.
   - `src/client/shared/{components/ui,lib,hooks}`:
     - the design system stays visually untouched;
     - `lib/errorMessage.ts` is the only place an error becomes text.
   - `src/shared/result.ts` defines `Result<T, E> = { ok: true; data } | { ok: false; error }`.
   - `src/test-support/` holds the test-only helpers.
2. **View models.**
   - A use-case component makes exactly one behavioral hook call, `use{Component}`, destructures it and renders.
   - The component body has no `useState`, `useEffect`, `useMemo`, `useCallback`, data hooks or router. An inline arrow only adapts arguments.
   - The view model returns a discriminated union (pending, error, empty, content), and guard clauses narrow it.
   - Presentation children have no hooks. A child gets its own view model only if it has its own behavior.
3. **State and effects.**
   - Server state is separate from UI state.
   - Single-purpose data hooks return data plus status, with no toast or navigation.
   - Side effects live in the view model and are triggered by events.
   - `useEffect` only syncs with external systems (stream, timers, observers).
   - No global state without need.
4. **Forms.** React Hook Form plus `zodResolver`:
   - the schema owns all validation;
   - `defaultValues` are complete;
   - edits go through `values`, never `useEffect` plus `reset`;
   - `Controller` fields get a label and an error tied by id;
   - server errors go through `setError`.

   Show the `package.json` diff before installing dependencies.
5. **Errors.**
   - The HTTP client turns an API error code into a `Result`.
   - `errorMessage.ts` picks the text by code, network failure included.
   - Components receive only ready strings and flags.
6. **Types.** No `any`, `!` or `as` to silence the compiler. API types are the single source.

## C. Tests
- **Pyramid:** most tests on pure domain rules, then use cases, then the boundaries (API, tools, view models), and few e2e.
- **Backend:**
  - every use case moved to `Result` gets tests for `Ok` and for each `Err`;
  - exhaustiveness tests for the error maps;
  - a contract test that unexpected errors do not leak a stack trace or a message;
  - the existing fakes keep isolating infrastructure.
- **Frontend:**
  - view-model tests with `renderHook`, covering every state and transition;
  - component tests with the view model mocked, one per rendered state;
  - `errorMessage` tests per code;
  - existing pure-logic tests move, without changes.
- **Determinism:**
  - an injectable clock and injectable ids;
  - factories in `test-support/`;
  - no `sleep` and no real-time assertions;
  - property tests (hypothesis / fast-check) where invariants exist, with a fixed seed.
- **Mocking:** never mock our own code; mock only external edges (network, the LLM through the scripted model, the browser).
- **Coverage:** no percentage target.
- **Layout:** tests mirror the source by context and layer.

## Constraints
- **Gates:** `make check` and `make check-web` are green on every commit, except the red half of a TDD pair. At the end, `make e2e` and `make test-pg` must pass too. A paid `make evals` needs the owner's approval.
- **TDD:** pairs `test(<ctx>): <behavior> (red)` → `refactor(<ctx>): <behavior>`, in small slices, with the app working between slices.
- **Slice order:**
  1. `shared/result.py` plus catalog;
  2. orders;
  3. policies;
  4. support and the tools;
  5. `api/` error maps;
  6. frontend warmup;
  7. auth;
  8. catalog;
  9. chat, last.
- **Git:**
  - branch `refactor/domain-architecture`;
  - Conventional Commits with the context as scope;
  - the `Co-Authored-By` trailer;
  - merge commit, never force-push, never rewrite `main`;
  - no merge without the owner's approval.
- **Language:** code, identifiers, commits and engineering docs in English. What the store's customer reads stays in pt-BR.
- **Docs ship with the code:**
  - AGENTS.md: folder map, layer table, Result and error-code rules, the view-model pattern;
  - two `.claude/rules/` files with `paths:`, one for the backend and one for the frontend;
  - ADRs: "domain errors as values", "frontend domain folders and view-model pattern", "error mapping at the boundaries";
  - lint enforcement: `domain/` imports no framework, and `ui/` has no hooks.
- **When the pattern does not fit** (the LangGraph graph, chat streaming, MCP), stop and ask the owner, explaining the alternative.
- **Neutral naming:** describe the patterns by what they are ("domain-oriented folders", "view-model pattern", "Result pattern", "domain error codes"). Never name the codebase they were studied from.
