# 0008. Gemini as the hosted demo default

## Context

The hosted demo is opened by evaluators who expect an answer within seconds. The Gemma GPU app has a cold start of about 3.5 minutes, and the Modal budget was $8 of credit with no card on file, which a GPU kept warm would drain quickly ([scaling and cost](../scaling-and-cost.md), sections 3 and 5).

## Decision

The hosted demo runs Gemini 3.8 Flash, with the scope guard on Flash-Lite. `make deploy-api` defaults to `API_PROVIDER=gemini`. Gemma 4 31B on the H100 remains measured and available with `make deploy-api API_PROVIDER=gemma`, with no code change.

## Consequences

- No GPU wait for an evaluator, and the credit is not spent on idle GPU time.
- Gemini passed 21 of the 22 eval cases with no AI tells.
- Replies are slower than the target: p50 is 7.30 s against a goal of 3 s or less, because the guard and the agent run one after the other. This target is missed.
- The demo does not show Gemma's voice; that comparison lives in the eval reports.

## Alternatives

- Gemma by default with a warm-up screen: meets 3 s once warm, but an evaluator may wait minutes or hit an empty credit.
- A GPU kept warm during store hours: about $837/month on an H100, which the budget does not allow.

Source: [scaling and cost](../scaling-and-cost.md), sections 1 and 3; [design spec](../superpowers/specs/2026-11-05-emporio-agent-design.md), section 7.2.5.
