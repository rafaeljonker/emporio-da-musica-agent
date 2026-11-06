# 0002. Gemma 4 31B, self-hosted on Modal

## Context

The agent needs a model that calls the right tool, states the right fact and sounds like a store attendant. We compared nine models on 14 scenarios with the real tools ([model selection](../model-selection.md)). Gemma 4 31B had the most human voice (4.8 of 5) and, after the prompt was tightened, called the right tool in 14/14 scenarios. Its two remaining misses were false negatives of the verifier, so the effective score is 14/14.

## Decision

Run Gemma 4 31B as open weights on vLLM, serverless on Modal. The default GPU is the H100 with FP8 weights ($3.95/h). The L40S ($1.95/h) is half the price per hour, but its median reply of 4.93 s misses the 3 s target and it costs more per reply (see [scaling and cost](../scaling-and-cost.md), section 1).

## Consequences

- Best voice, no per-token bill, and customer data stays on our GPU.
- Cold start is about 204 s on the H100 against a 30 s target. The target is not met ([scaling and cost](../scaling-and-cost.md), section 2).
- Because of that cold start, the hosted demo defaults to a hosted API model instead ([0008](0008-gemini-hosted-default.md)). Gemma is still one flag away.

## Alternatives

- Gemini, OpenAI or Anthropic as the only option: no cold start, but no control over the model and a per-token cost.
- Other open models from the comparison: none matched Gemma's voice with the same accuracy.

Source: [model selection](../model-selection.md); [scaling and cost](../scaling-and-cost.md), sections 1 and 2; [design spec](../superpowers/specs/2026-11-05-emporio-agent-design.md), section 7.2.5.
