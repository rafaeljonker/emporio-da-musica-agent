# 0006. Model providers chosen by a flag

## Context

The agent should run on Gemma, Gemini, OpenAI, Anthropic or a local model, so the choice can follow cost, latency and availability. The providers differ only in model name, key and base URL.

## Decision

A single `make_chat_model` function wraps LangChain's `init_chat_model`. The provider comes from `LLM_PROVIDER` (or `PROVIDER=` in the Makefile): `gemma`, `gemini`, `openai`, `anthropic` or `local`. Each provider needs its own key; a missing value stops startup with an error that names the variable and the alternatives. There is no silent fallback to another provider.

## Consequences

- Switching provider is a configuration change; the same evals run on any of them.
- A failed Gemma never quietly becomes a paid API call, and a wrong key is caught at startup rather than mid-conversation.
- One factory is less code than a port with an adapter class per provider.
- Every provider shares one prompt, so provider-specific tuning (such as Gemini's thinking level) lives in the factory.

## Alternatives

- A port with one adapter class per provider: more files for the same few differences.
- Automatic fallback when a provider fails: it hides cost and quality changes from the operator.

Source: [design spec](../superpowers/specs/2026-11-05-emporio-agent-design.md), sections 5, 7.2.3 and 7.14.
