# Component Plan

> Phase: design | Project: emporio-chat | Generated: 2026-11-05 | Target: shadcn (greenfield `frontend/`)
> Install list: [../../brief/install-manifest.md](../../brief/install-manifest.md). Brand specs: `.design/branding/emporio-da-musica/patterns/components/`.

## Reuse (as-is, tokens only)

| Component | Source | Screens |
|---|---|---|
| Card | shadcn `card` + `.surface-wood` | login |
| Avatar | shadcn `avatar` (Boca disc, `alt=""`) | chat, warm-up |
| Label | shadcn `label` (16 px 600) | login |

## Refactor (shadcn primitive, brand override)

| Component | Source | Changes | Screens |
|---|---|---|---|
| Button | shadcn `button` | cva per button.md: pill, `--primary-hover`, settle-press, brand focus (+ cream gap on primary), `size="icon"` 44 px send; destructive label fix | all |
| Input | shadcn `input` | paper fill, `--input` border, 16 px, outline focus, no ring | login |
| Textarea | shadcn `textarea` | `rounded-full`, auto-grow 1–5 lines, Enter sends | chat, warm-up |
| Select | shadcn `select` | select.md: honey highlight, walnut selected outline + `Check` + honey marker, two-line items | chat, warm-up |
| Badge | shadcn `badge` | spruce/hairline variant, moss text for honest badge; never default (terracotta) | chat (ProductCard) |

## New (shared, brand custom, `frontend/src/chat/`)

| Component | Purpose | Spec | Screens |
|---|---|---|---|
| ChatShell | layout: rail, strip, notice, body slot, composer; owns session + warm state | screen-01 | chat, warm-up |
| WoodRailHeader | identity + Sair | wood-rail-header.md | chat, warm-up |
| DemoStrip | `<aside aria-label="Demonstração">`: tag + CustomerSelector + MetricsDetails; content in the transcript column | customer-selector.md | chat, warm-up |
| ChatTranscript / MessageGroup / ChatBubble | `role="log"`, grouping, avatar on last, sr prefixes | chat-bubble.md | chat, warm-up (queued) |
| TypingIndicator | `role="status"`, dot-pulse | typing-indicator.md | chat |
| HandoffBubble | limit admitted | handoff-bubble.md | chat |
| ProductCard | honest card, promo/PIX lines | product-card.md | chat |
| Composer | textarea + send; queue mode during warm-up | input.md | chat, warm-up |
| MetricsPanel | `<dl>` last reply (tokens, "no modelo · na tela", cost + basis), session (incl. Aquecimento), per-turn history | screen-01 § Metrics | chat, warm-up |
| StatusRegion | persistent `role="status"` in the shell's `<main>`, outside WarmupStatus; never unmounted with the content it announces | screen-02 § Accessibility | chat, warm-up |

## New (local)

| Component | Screen | Purpose |
|---|---|---|
| WarmupStatus (`frontend/src/warmup/`) | warm-up | stages, count-up timer from `started_at`, network/long-wait/failed blocks, pinned compact line below `md` when queued, variant copy by `mode` |
| LocalModeNotice | chat | persistent slow-reply notice for `local_cpu` |
| MetricsDetails | chat, warm-up | native `<details>` in the demo strip; summary shows session totals (16px) |
| LoginForm | login | fields, error line, `aria-busy`, triggers `/warm` |
| RosetteDrawing, PegsDrawing | chat empty, warm-up | inline SVG line drawings, `aria-hidden` |

## Hooks / state (no extra deps)

`useSession` (login/logout), `useWarmStatus` (seeded from the login response, poll 1 s until ready/failed; exposes `mode`, `stage`, `startedAt`, `expectedSeconds`, `elapsed = now - startedAt`, `networkError` after 3 consecutive poll failures), `useChatStream` (SSE → typing/bubble/metrics/done/error; honors `delay_ms`), `useQueuedMessage` (one queued group, lines joined by `\n`, undo, `sessionStorage` persistence across reload and re-login, flush once on ready). No toast, no ScrollArea, no collapsible install.

## Related
- [../../brief/target-adaptations.md](../../brief/target-adaptations.md)
