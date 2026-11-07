# 0012. Remote MCP with bearer tokens

## Context

The ten store tools were served over MCP on stdio only, so a reviewer had to clone the repo, run Postgres and `make mcp`. The hosted demo (emporio.fastmind.site) could serve them too, but a remote server needs to know who is calling: the model must never pass a customer id.

## Decision

The web app serves the same tools over stateless streamable HTTP at `/mcp` (FastMCP, JSON replies, one container behind the Cloudflare Worker). Every request carries `Authorization: Bearer <token>`. `MCP_TOKENS` (Modal secret `emporio-mcp`) maps each token to one identity, a customer id or `anon`; an unknown id fails startup, and an empty setting leaves `/mcp` unmounted. The API's gate binds the token's identity per request and the tools read it through a context provider, so no identity reaches a tool schema.

Bearer and not OAuth: a static token took hours, OAuth (authorization server, dynamic client registration, consent) takes days. The cost is that claude.ai connectors, which require OAuth, cannot use it; Claude Code and Claude Desktop (through `mcp-remote`) can.

Limits: an invalid or missing token is 401 `invalid_token` with `WWW-Authenticate: Bearer`; failures are limited to 10/min per client IP and valid calls to 60/min per token (429). Tokens are compared in constant time and never logged.

## Consequences

- Tokens are shared secrets handed out with the demo credentials; rotating means replacing the secret and redeploying.
- Limits live in process memory, like the rest of the web state (one container).
- Upgrade path: FastMCP's OAuth support (an `AuthProvider` with an external identity provider), mapping the OAuth subject to a customer the same way the token does today; the context provider stays.

Source: [design spec](../superpowers/specs/2026-11-05-emporio-agent-design.md), section 7.12.
