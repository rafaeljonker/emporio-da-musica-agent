---
paths:
  - "backend/src/**"
---
- Expected failures return `Result` (`emporio.shared.result`: `Ok` / `Err`); raise only for the unexpected (bug, infrastructure down, bad config or data).
- One `StrEnum` of codes per context in `<ctx>/domain/errors.py`; a code is data, never a message.
- Domain and application code has no `try/except`; adapters catch infrastructure errors and map them (e.g. `StoreUnavailable`).
- Each boundary maps a code once: `api/errors.py` to HTTP, `agent/tools/<ctx>.py` to pt-BR text. Build maps with `match` ending in `case _: assert_never(code)` and test every enum member.
- Never decide on an error's message text; match on the type or the code.
- Unexpected API errors return the generic 500 body; log server-side, never echo the message.
