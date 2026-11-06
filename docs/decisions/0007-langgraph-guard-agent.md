# 0007. LangGraph: guard, then agent and tools

## Context

A store attendant must stay in scope, resist abuse and never invent prices or deadlines. Putting all of that in one prompt makes the agent harder to test and easier to derail.

## Decision

The conversation is a LangGraph graph: a `guard` node, then an `agent` node that loops with a `tools` node. The guard runs on every turn and classifies the message as `loja`, `acessorio`, `fora_de_escopo` or `abuso`. An `abuso` message gets a fixed reply and never reaches the agent. If the classifier fails, the message is treated as `loja`, since the agent has its own scope rules. Tools are plain functions called in-process; the same functions are also exposed over FastMCP for external clients, and a contract test keeps the two in sync.

## Consequences

- Abuse and out-of-scope messages are handled cheaply and predictably.
- The guard adds a second, sequential model call per turn, which costs latency ([scaling and cost](../scaling-and-cost.md), section 3). The hosted demo runs it on a smaller model to limit this.
- In-process tool calls avoid a network hop; MCP clients get the same tools without a second implementation.

## Alternatives

- One prompt that handles scope and abuse itself: fewer calls, but untestable in isolation.
- Routing by keywords: brittle for Portuguese free text.

Source: [design spec](../superpowers/specs/2026-11-05-emporio-agent-design.md), sections 7.2.3 and 7.12.
