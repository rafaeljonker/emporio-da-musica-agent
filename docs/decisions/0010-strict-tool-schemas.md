# 0010. Strict tool schemas

## Context

The model fills in the arguments of every tool call. Models sometimes add unknown fields or send numbers as strings, such as `"89.90"`. Silently accepting or coercing them can turn a wrong argument into a wrong price or a wrong order.

## Decision

Every agent tool takes a strict Pydantic model: `extra="forbid"`, money as a JSON number, and numeric strings rejected. When validation fails, the error goes back to the model as a short, recoverable message instead of an exception, so it can correct the call. The customer identity never appears as an argument; it reaches tools through the runtime context.

## Consequences

- Malformed calls fail loudly and the model usually fixes them on the next step.
- The final Gemini eval run ([report](../../backend/evals/reports/gemini.md)) ran on code that already had these schemas (commit `58a4253`).
- A provider that cannot produce clean numbers needs prompt work instead of looser validation.

## Alternatives

- Lenient parsing that coerces strings to numbers: fewer retries, but hides model errors.
- Raising an exception on bad input: ends the turn instead of letting the model recover.

Source: [design spec](../superpowers/specs/2026-11-05-emporio-agent-design.md), sections 7.2.3 and 7.2.5.
