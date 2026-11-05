# Scope

> Phase: brief | Project: emporio-chat | Generated: 2026-11-05
> Source: [../BRIEF.md](../BRIEF.md) · Brand: [STYLE.md](../../../branding/emporio-da-musica/patterns/STYLE.md)

## Screen list (prioritized)

| # | Screen | Priority | Purpose | Key states |
|---|--------|----------|---------|------------|
| 1 | Chat | P0 | The demo itself: conversation with the agent, judged on voice and accuracy | empty, agent typing, 1–3 sequential bubbles, handoff, product card, send failed, customer switched, anonymous, metrics open/closed, local-mode notice |
| 2 | Warm-up (chat body state) | P0 | Explain the GPU cold start honestly and keep the user productive (queue a message) | Modal GPU: `server_starting` → `model_loading` → `ready`; long wait (> 2 × expected); failed; message queued; local CPU variant; provider API (screen skipped) |
| 3 | Demo login | P1 | Gate the hosted demo and trigger `/warm` on success | rest, submitting ("Entrando…"), invalid credentials, network error |

Why this order: the chat is what gets evaluated; the warm-up is the first thing the evaluator sees after login and the most likely source of a bad first impression (175 s cold start today, target ≤ 30 s); login is a standard form with brand specs already written.

### Flow

```
Login ──POST /auth/login ok──► POST /warm (fire and forget) ──► Chat shell
                                                               ├─ mode = provider_api → chat ready immediately
                                                               ├─ mode = modal_gpu    → warm-up body, poll /warm/status (~1 s)
                                                               └─ mode = local_cpu    → warm-up body (local copy), then chat + persistent slow-reply notice
```

The warm-up is rendered **inside the chat shell** (wood rail + demo strip + composer stay on screen), per [wood-rail-header.md](../../../branding/emporio-da-musica/patterns/components/wood-rail-header.md) "agent offline / warming" state. This is what makes "type now, it sends when ready" possible.

## Component scope

### Brand custom (Tier 3, built from brand specs; no shadcn equivalent)

| Component | Brand spec | Used on |
|-----------|-----------|---------|
| WoodRailHeader | [wood-rail-header.md](../../../branding/emporio-da-musica/patterns/components/wood-rail-header.md) | chat, warm-up |
| ChatTranscript + ChatBubble + MessageGroup | [chat-bubble.md](../../../branding/emporio-da-musica/patterns/components/chat-bubble.md) | chat |
| TypingIndicator | [typing-indicator.md](../../../branding/emporio-da-musica/patterns/components/typing-indicator.md) | chat |
| HandoffBubble | [handoff-bubble.md](../../../branding/emporio-da-musica/patterns/components/handoff-bubble.md) | chat |
| ProductCard | [product-card.md](../../../branding/emporio-da-musica/patterns/components/product-card.md) | chat |
| WarmupStatus | [warmup-status.md](../../../branding/emporio-da-musica/patterns/components/warmup-status.md) | warm-up (adapted, see target-adaptations) |
| CustomerSelector (demo strip) | [customer-selector.md](../../../branding/emporio-da-musica/patterns/components/customer-selector.md) | chat, warm-up |
| Composer | [input.md § Chat composer](../../../branding/emporio-da-musica/patterns/components/input.md) | chat, warm-up |
| MetricsPanel (new, project-level) | none yet; defined in design phase | chat (demo strip) |

### shadcn primitives (Tier 2 overrides)

`button` ([button.md](../../../branding/emporio-da-musica/patterns/components/button.md)), `input` + `label` + `textarea` ([input.md](../../../branding/emporio-da-musica/patterns/components/input.md)), `select` ([select.md](../../../branding/emporio-da-musica/patterns/components/select.md)), `card` (login card), `avatar` (Boca disc in rail and agent groups), `badge` (honest badge base). Install list: [install-manifest.md](./install-manifest.md).

## Project boundaries

**In scope**
- The three screens above, mobile-first (360 px) up to desktop (`max-w-2xl` chat column), light and dark.
- pt-BR UI copy per [voice-and-tone.md](../../../branding/emporio-da-musica/strategy/voice-and-tone.md).
- Rendering of the SSE event stream from `/chat`: typing, bubble (text | handoff | product), metrics, done, error.
- "Conversar como…" with every customer in `data/customers.csv` (via `/customers`) plus "Sem identificação" (anonymous: the agent asks for order number + e-mail/phone).

**Out of scope**
- Real WhatsApp, customer login, admin or staff console, order/stock writes.
- Logout beyond clearing the demo session; password reset; sign-up.
- Token-by-token streaming into bubbles (bubbles arrive complete).
- Marketing/launch assets; logo vectorization (brand task, tracked in identity/logo-directions.md).

## Success criteria

- WCAG 2.2 AA: no critical findings in project critique; every text pair uses a recorded ratio from the brand `.yml`.
- Every wait is explained with real backend data: no client-advanced stage, no countdown, no spinner, no percentage.
- A message typed during warm-up is sent exactly once, automatically, when `/warm/status` reports `ready`.
- Zero AI tells in UI copy (no em dash, no stock phrases, no emoji).
- `make e2e` (Playwright) passes: login → warm-up → conversation → bubbles.

## Dependencies

| Dependency | Owner | Needed by |
|-----------|-------|-----------|
| `/auth/login`, `/warm`, `/warm/status` (stage + `mode` + `expected_seconds`), `/chat` SSE, `/customers` | backend `api/` (phase 5) | build |
| SSE event schema incl. `kind: handoff | product`, honest flag, per-turn metrics | backend `support` | design (shape), build |
| Measured cold start and median reply latency (for copy numbers) | Modal deploy measurements | build (config values, not hardcoded in design) |
| Boca avatar asset (raster concept; SVG pending) | brand | build |
| Theme CSS (`emporio-da-musica.theme.json`) + brand extensions | brand patterns | build |

## Issue framing

No GitHub issue; work ships as one PR per project phase.
- **This PR (`feat/design`):** brief → design (3 screens + shared states) → critique fixes.
- **Phase 5 build PR, suggested commit slices (each shippable and testable on its own):**
  1. `chore(frontend)`: Vite + Tailwind v4 + shadcn init, theme + brand extensions, fonts, Tier 2 overrides.
  2. `feat(frontend)`: demo login + session + `/warm` trigger.
  3. `feat(frontend)`: chat shell (wood rail, transcript, bubbles, typing, composer) on `/chat` SSE.
  4. `feat(frontend)`: warm-up body state with `/warm/status` polling, queued message, local/provider variants.
  5. `feat(frontend)`: HandoffBubble, ProductCard, CustomerSelector, MetricsPanel.
  6. `test(e2e)`: Playwright login → warm-up → conversation.

## Related
- [target-adaptations.md](./target-adaptations.md) · [install-manifest.md](./install-manifest.md) · [../BRIEF.md](../BRIEF.md)
