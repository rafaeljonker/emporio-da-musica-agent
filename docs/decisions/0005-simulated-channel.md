# 0005. A simulated WhatsApp channel

## Context

The case is a WhatsApp support agent. A real WhatsApp integration needs a business account and approval, which an evaluator cannot reproduce in minutes. The behavior that matters (short messages, human pacing, identifying the customer) can be shown without it.

## Decision

Ship a React web chat that imitates WhatsApp. Each reply is a few text bubbles, each with a server-computed `delay_ms` that the client waits out, so the whole turn runs first and there is no token streaming. A demo login protects the page, the evaluator picks an identity from the seed customers, and every session gets its own thread id. The agent talks to a channel port, so a real WhatsApp adapter can be added later without touching the agent.

## Consequences

- An evaluator can try the agent with a link and a login, with no phone and no account.
- Pacing is deterministic and testable because the server never sleeps.
- Waiting for the full turn feels slower than streaming tokens, which is the cost of showing finished bubbles.
- Real WhatsApp, human handoff and product cards are not built.

## Alternatives

- The WhatsApp Business API: realistic, but not reproducible by a reviewer.
- A plain chat box with token streaming: easier, but it hides the multi-bubble voice the case asks for.

Source: [design spec](../superpowers/specs/2026-11-05-emporio-agent-design.md), sections 7.2.4 and 7.3.1.
