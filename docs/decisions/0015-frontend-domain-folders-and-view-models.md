# 0015. Frontend domain folders and view models

## Context

Components mixed fetching, session expiry (nine `instanceof SessionExpired` checks and an `onExpired` prop drilled into four children), focus, error text and markup; `CatalogDialog` held eleven `useState`s and its own validation. Nothing but review kept logic out of rendering.

## Decision

`src/client/<domain>/{domain,ui,useCases/<case>,__tests__}` per domain (auth, catalog, chat, warmup), plus `client/shared` and `src/app`. Each use-case component calls one `use{Component}` view model that returns a discriminated union; `domain/` is pure TS and `ui/` is hookless, both fenced by oxlint. The HTTP client returns `Result<T, ApiError>`, `errorMessage.ts` alone turns a code into text, and a module-level listener carries session expiry to `useApp`. The catalog form is React Hook Form with a zod schema that owns every rule and message, validating on submit as before.

## Consequences

- Hooks are tested with `renderHook` against a stubbed `fetch`; the e2e keeps pinning the markup, so there are no component tests.
- A new API code fails typecheck until `ApiErrorCode` and `errorMessage` handle it.
- zod and RHF add about 70 kB to the bundle (past Vite's 500 kB warning).

## Alternatives

- A global store (Redux, Zustand): no state is shared across screens beyond the session, which one listener covers.
- Container/presenter components: two files per screen without a typed contract between them.
