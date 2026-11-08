# 0013. Domain errors as values

## Context

Expected failures (an unknown product, a foreign order, a plan past 12 installments, a name the store already uses) were exceptions under a shared `DomainError`. Config, CSV and database errors inherited it too, so the tools' `except DomainError` turned a bug into "Dado inválido.", and nothing forced a caller to handle a failure.

## Decision

Use cases and pure rules return `Result[T, E] = Ok[T] | Err[E]` (`shared/result.py`, frozen dataclasses) for expected failures. Each context owns one `StrEnum` of codes in `domain/errors.py` (`CatalogErrorCode`, `OrdersErrorCode`); a code is data, never a message. Domain and application code has no `try/except`. Exceptions stay for the unexpected: bugs, infrastructure down (`StoreUnavailable`), bad config or data, and invariants of constructors (`Money`, `Settings`). basedpyright's `reportMatchNotExhaustive` makes every `match` on a code exhaustive.

## Consequences

- A new code fails typecheck until every boundary maps it.
- `DomainError` is gone; a CSV or config error inside a tool is now a `ToolCrashed` (`TOOL_FAILURE`), no longer "Dado inválido.".
- Policies and support need no enum yet: their read paths have no expected failure (`Reply.failed` is already a value).
- Pydantic argument validation stays a separate channel (422 lists, tool retry hints).

- A data, config or bug error inside a tool is now unexpected: the agent gets the tool-failure text, and an MCP client gets FastMCP's masked tool error instead of "Dado inválido.".

## Alternatives

- Keep exceptions with a narrower base class: callers still are not forced to handle them, and messages tempt parsing.
- A Result library: one more dependency for sixteen lines; no bind/map helpers were needed.
