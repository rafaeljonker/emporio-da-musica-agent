# 0014. Error mapping at the boundaries

## Context

With errors as codes ([0013](0013-domain-errors-as-values.md)), something must turn a code into what a client reads. The API had a `_STATUS` dict for catalog writes and string literals elsewhere; the tools had texts spread across one 479-line module; an unhandled API error returned Starlette's plain-text 500.

## Decision

Each boundary translates a code exactly once, in one exhaustive map built from a `match` ending in `assert_never`:
- HTTP: `api/errors.py` holds `CATALOG_HTTP` and `API_HTTP` (code → status); the body is `{"detail": "<code>"}`, byte-identical to before. A global handler answers any unexpected exception with 500 `{"detail": "internal_error"}` and logs it server-side.
- Agent tools: `CATALOG_TEXT` and `ORDERS_TEXT` in `agent/tools/{catalog,orders}.py` (code → pt-BR text). `tools.base.safe` maps `StoreUnavailable` to `INDEX_UNAVAILABLE` and anything else to `ToolCrashed`, logged by type name only.
- Frontend: the same rule, one `errorMessage.ts` from wire code to pt-BR copy (frontend slices).

No layer parses an error message.

## Consequences

- Tests iterate each enum against each map, so a missing code fails at import and in CI.
- The tool turn, the SSE route and the MCP wrappers keep their shapes: Result stops at the tool function.
- The 500 body changed from plain text to JSON on a path that is a bug anyway.

## Alternatives

- `(status, message)` pairs in the API: the frontend already owns the copy and the wire carries codes only.
- Exception handlers per error class: hides the mapping across modules and is not exhaustive.
