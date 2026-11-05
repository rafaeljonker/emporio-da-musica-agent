# Design Index

> Phase: design | Project: emporio-chat | Generated: 2026-11-05 | Revised: 2026-11-05 (revision 1)
> Research skipped (designing from brief only). Brand law: [STYLE.md](../../../branding/emporio-da-musica/patterns/STYLE.md).

## Screens

| # | Screen | File | Components Used |
|---|--------|------|-----------------|
| 01 | Chat | [screen-01-chat.md](./screen-01-chat.md) | WoodRailHeader, DemoStrip, CustomerSelector, MetricsDetails, MetricsPanel, LocalModeNotice, ChatTranscript, ChatBubble, TypingIndicator, HandoffBubble, ProductCard, Composer |
| 02 | Warm-up (chat body state; GPU / local / provider variants) | [screen-02-warmup.md](./screen-02-warmup.md) | WarmupStatus, StatusRegion, WoodRailHeader, DemoStrip, ChatTranscript (queued bubble), Composer, Button |
| 03 | Demo login | [screen-03-login.md](./screen-03-login.md) | Card, Label, Input, Button |

## Shared

| Chunk | File | ~Lines |
|-------|------|--------|
| Personas | [shared/personas.md](./shared/personas.md) | 35 |
| Information architecture | [shared/information-architecture.md](./shared/information-architecture.md) | 42 |
| Navigation | [shared/navigation.md](./shared/navigation.md) | 35 |
| Micro-interactions (incl. bubble pacing, reduced motion) | [shared/micro-interactions.md](./shared/micro-interactions.md) | 42 |
| Responsive (360 → 1280) | [shared/responsive.md](./shared/responsive.md) | 24 |
| Component plan | [shared/component-plan.md](./shared/component-plan.md) | 55 |

## Mockups

Static, clickable HTML (no build). Open [mockups/index.html](./mockups/index.html) for the gallery (390 × 844 phone and 1280 × 800 desktop side by side).

| File | Shows |
|---|---|
| [mockups/login.html](./mockups/login.html) | login, "Entrando…", invalid credentials, network error, success → warm-up |
| [mockups/warmup.html](./mockups/warmup.html) | `?variant=gpu|local|api`; status-first mobile order, count-up from `started_at` (survives reload/retry), network error, long wait without retry, failure + retry, queued message with undo and pinned status line, flush on ready |
| [mockups/chat.html](./mockups/chat.html) | scripted 4-scene demo (price + honest card, accessory, identified order, handoff, queued message); selector divider without clearing; partial-reply error; collapsed Métricas with session totals and history |
| `mockup.css`, `mockup.js` | brand tokens as CSS custom properties, Lucide sprite, shared transcript logic (mockup only) |

## Decided

Metrics placement: collapsed "Métricas" `<details>` in the demo strip (decided 2026-11-05). Summary carries session totals; the panel holds the last reply, the session and a per-turn history. Specified in screen-01 § Metrics.

## Brand fidelity self-check

- [x] Never/always constraints: terracotta only on Entrar, send, Tentar de novo; no blue; no Fraunces in chat; no spinner/progress bar/percentage; no emoji; no markdown in bubbles; 16 px floor for interactive text (Métricas summary and "Manda de novo?"/"Desfazer" link buttons now 16px).
- [x] Bold Bet 1 (one color means act): all screens. Bold Bet 2 (Boca avatar): rail, groups, warm-up. Bold Bet 3 (honest warm-up): screen 02, now with backend-owned time. Bold Bet 4 (wood on paper): login card, canvas grain, wood rail. Bold Bet 5 (walnut user bubbles): screen 01.
- [x] Effects only from vocabulary: warm-darken, settle-press, fade-arrive, ring-breathe (one breath), dot-pulse (+ wood-rail surface).
- [x] Dials: variance 3 (one Fraunces moment per non-chat screen), motion 2, density 4 (warm-up lighter on phones: one merged note).
- [x] No generic surfaces: shadow only `shadow-sm` on ProductCard and metrics panel (paper sheets).

## Revision 1 (2026-11-05)

Source: [critique/prioritized-fixes.md](../critique/prioritized-fixes.md) (C = Critical, I = Important, P = Polish) and [critique/accessibility-fixes.md](../critique/accessibility-fixes.md) (A-xx).

| Fix | Addressed in |
|---|---|
| C1 warm-up status below the fold | screen-02 § Layout, § Variants, § Responsive; responsive.md; mockup `warmup.html` (order, `.full`, `.pin`), `mockup.css` (`.warm`, Boca 48/72, `.warm.compact`) |
| C2 status/time only from backend | screen-02 § Backend contract, § States (network error, long wait without retry, retry keeps `started_at`); screen-03 § Flow; target-adaptations WarmupStatus; component-plan `useWarmStatus`; `warmup.html` simulated backend in `sessionStorage` |
| C3 bubble pacing vs "2 s" | micro-interactions § Bubble pacing; screen-01 § SSE, § Metrics ("no modelo · na tela"); screen-02 § Variants note; `mockup.js` `reply()` (bubble 1 at 0 ms, 3 s cap) |
| C4 remove the dropped per-turn metrics alternative | screen-01 (header, layout, components, SSE, § Metrics, interactions); INDEX; component-plan; information-architecture; navigation; responsive; personas; exports/INDEX; mockups `index.html` (3b gone), `chat.html` (toggles gone), `mockup.js`, `mockup.css` |
| C5 14px interactive text | screen-01 § Metrics, § States; `mockup.css` `.metrics summary` 1rem 600, `.btn-link` own 1rem |
| I1 selector keeps the thread | screen-01 § States/Interactions; screen-02 § States; `chat.html` `switchTo`, `warmup.html` selector listener |
| I2 metrics worth opening | screen-01 § Metrics (summary session totals, last reply, Aquecimento, cost basis, history, 40dvh, "filtro"); `mockup.js` `renderMetrics` |
| I3 queued control + announcements | screen-02 § States (Desfazer, more sends, reload, expiry); navigation.md; component-plan `useQueuedMessage`; `warmup.html` `queue`/`undo` |
| I4 partial reply error | screen-01 § SSE, § States; `mockup.js` `partialError`, `chat.html` "Erro no meio da resposta" |
| I5 no forced keyboard on ready | screen-02 § Accessibility (focus rule); `warmup.html` `ready()` |
| I6 HandoffBubble honesty | screen-01 § States (Handoff); `chat.html` scene 4 |
| I7 explain the demo strip | screen-01 § States (Empty); `chat.html` / `warmup.html` empty state |
| I8 login sets expectation | screen-03 § Layout; `login.html` note |
| I9 desktop alignment | screen-01 § Layout; responsive.md; navigation.md; `mockup.css` `.rail-inner`, `.strip-inner` in `.column` |
| A-01 selector SC 3.2.2 | screen-01 § States/Interactions/Accessibility (instant-apply kept: no clear, no focus move); `chat.html` |
| A-02 live region outside the panel | screen-02 § Accessibility; component-plan StatusRegion; `warmup.html` `#warm-live`, delayed focus |
| A-03 short-viewport collapse | screen-01 § Layout; responsive.md; `mockup.css` `.body` floor + `max-height: 480px` rule |
| A-04 send keeps focus | screen-01 § Interactions; `mockup.js` `aria-disabled`; `mockup.css` |
| A-05 retry focus | screen-02 § States (Retry); `warmup.html` focuses `#warm-title` |
| A-06 long-wait announcement | screen-02 § States; `warmup.html` `live()` once |
| A-07 typing-dot contrast | screen-01 § Components; micro-interactions; `mockup.css` `--typing-dot` |
| P1 ProductCard heading | screen-01 § Components; `mockup.js` `.product-name` |
| P2 "tô aqui pra ajudar" | `chat.html` scene 2 ("Se for violão, é comigo.") |
| P3 duplicated 2 s | screen-02 § Variants (merged note) |
| P4 type-ahead said once | screen-02 § Variants (placeholder invites, note explains) |
| P5 build notes (partial) | auto-scroll near bottom + `overflow-wrap` + login first empty field in mockups; see Deferred |
| P6 dark-mode wordmark | screen-03 § Responsive; `login.html` |
| P7 local long-wait threshold | screen-02 § States (per-mode expected) |
| A-08 "Entrando…" status | screen-03 § States; `login.html` `#login-live` |
| A-09 stage marker (partial) | `mockup.css` current stage `--warning` 5.40:1 on cream, 4.91 on #F3E9D8, 4.22 on spruce (non-text border, needs 3:1: passes); see Deferred |
| A-10 landmarks/headings | screen-01 § Accessibility; information-architecture heading model; mockups `aside`, `form aria-label`, `p.product-name`, `.mp-h`, `aria-current="step"` |
| A-11 `aria-invalid` | screen-03 § States; `login.html` |
| A-12 breathing avatar | screen-02; micro-interactions; `mockup.css` one iteration |
| A-13 rem units | responsive.md; `mockup.css` |
| A-14 announcement volume/scroll | screen-02 § States; `mockup.js` `add()`; `warmup.html` queued bubbles |
| A-15 long tokens | `mockup.css` `.bubble`, `.product` |
| A-16 dropped-alternative housekeeping | see C4 |

## Deferred to build

- P5: Fontsource instead of the mockup's Google Fonts `@import` (STYLE "always"; noted in `mockup.css`); "Novas mensagens" pill (specified in screen-01, not mocked).
- P8 to P11 `[STYLE]`: grain exemption for 14–16px text, selector label size, `underline-thicken` in the vocabulary, composer placeholder exception. Route to `/gsp-brand-refine`.
- A-07 brand doc: update `typing-indicator.md` token note ("muted walnut in light, lighter honey in dark") via `/gsp-brand-refine`.
- A-09 dark-mode card/bubble edges `#7A6455`: advisory, only if boundaries must identify the component.
- Accessibility verification checklist (accessibility-fixes.md): real VoiceOver/NVDA pass on announcement order and a 320 × 256 zoom test on the built app.
