# Design Critique

> Phase: critique | Project: emporio-chat | Generated: 2026-11-05
> Reviewer: GSP Design Critic | Inputs: [BRIEF.md](../BRIEF.md), [brief/](../brief/), [design/](../design/) incl. HTML mockups (read as source), brand [STYLE.md](../../../branding/emporio-da-musica/patterns/STYLE.md). Research skipped.
> Owner decision: metrics placement = **option A** (collapsed "Métricas" in the demo strip). Option B is out of scope for this critique; leftover B references are flagged in § Consistency.

## Verdict

| Lens | Score | Level |
|---|---|---|
| Nielsen heuristics | **33/50** | Solid base, several major gaps |
| Brand contract (STYLE.md) | **18/25**, **automatic Fail** | Fails only because of 14px interactive text (constraint dimension = 1). Fixing two font sizes clears it |
| Visual taste | **55/75** | Level 4, Refined |

**Overall:** a strong, honest direction that is close to ready to build. The honesty rules (stages come from the backend, the timer counts up, the expected time is rounded up, no countdown) are the best thing in the project. The weak spots are where honesty meets the screen size and the clock: on a 360 px phone the warm-up's real status sits below the fold, the client shows a first stage the backend never reported, the timer resets on retry and reload, and bubble pacing makes the "2 s" claim look wrong next to the metrics. Fix the 5 Critical items in [prioritized-fixes.md](./prioritized-fixes.md) before phase 5.

---

## 1. Strategy alignment

- **Audience fit: good.** Camila, the evaluator, reaches a conversation fast: login → warm-up with a type-ahead queue → chat. The demo strip separates demo tools from store content, which protects the "human store on WhatsApp" goal ([information-architecture.md](../design/shared/information-architecture.md)).
- **Business goal ("every wait is explained"): mostly met.** On desktop, yes. On mobile, the explanation is there, but the stage list and timer start about 290 px into a ~670 px panel (see § Mobile), so the first thing a phone user sees is the headline and a paragraph, not the status.
- **Scope: right-sized.** Three screens, one route, native `<details>`, no toast, no ScrollArea. The design avoids building things it doesn't need.
- **Gap:** the evaluator's job is to judge "lógica, clareza e iniciativa" and tool accuracy. Option A shows numbers but not *what happened* in a turn (tool called, handoff logged). One line per turn in the metrics panel would close that gap without touching the transcript (see prioritized-fixes I-2).

## 2. Brand contract (X/25)

| Dimension | Score | Evidence |
|---|---|---|
| Constraint adherence | **1** | Never-rule "Body or interactive text under 16px": the "Métricas" `<summary>` inherits `.metrics { font-size: 14px }` ([mockup.css](../design/mockups/mockup.css)); the "Manda de novo?" link button sits in a 14px error line with `font: inherit` ([screen-01-chat.md](../design/screen-01-chat.md) § States). Everything else holds: terracotta only on Entrar, send and Tentar de novo; no blue; no spinner, bar or percentage; no Fraunces in bubbles; no emoji in UI copy; no markdown |
| Pattern fidelity | 4 | Bubbles, rail, ProductCard, handoff and select follow the specs. Gap: ProductCard uses `<h3>` inside a chat state that has no `<h2>` |
| Effects vocabulary | 5 | Only warm-darken, settle-press, fade-arrive, ring-breathe, dot-pulse. `underline-thicken` is in STYLE's hover table but missing from the vocabulary list. That is a brand-side inconsistency, not a project one |
| Intensity calibration | 3 | Density dial says the warm-up is "airy, few words". The GPU variant stacks 8 text blocks (h2, explanation, expected, 3 stages, timer, production note, type-ahead note, long-wait). That is airy on desktop and crowded on a phone |
| Bold bet presence | 5 | All five are visible: one act color, the Boca avatar in rail, groups and warm-up, the honest warm-up, wood on paper, walnut user bubbles |

**Brand-side conflicts** (route to `/gsp-brand-refine`, not to this project):
- "Texture behind … any text under 18px" (never) conflicts with "paper grain on the cream canvas" and "wood grain on the login card" (always/surfaces). The warm-up panel and login card put grain behind 14–16px text, as the brand prescribes.
- The customer-selector spec puts the label at 14px; the Input pattern says labels are 16px.
- Input "never placeholder-only" vs. the chat composer (placeholder + `aria-label` only). The composer exception is a reasonable chat convention, but STYLE should say so.

## 3. Usability: Nielsen (X/50)

| # | Heuristic | Score | Notes |
|---|---|---|---|
| 1 | Visibility of system status | 3 | Strong: real stages, count-up timer, typing indicator, queued line "Vai assim que o assistente ficar pronto". Major gaps: (a) at 360×640 the stage list and timer are below the fold; (b) before the first `/warm/status` reply, the first stage is shown as current, a state the backend never reported, and in `local_cpu` mode the stage is wrong ("Ligando a GPU" on a CPU machine); (c) elapsed time restarts at 0 on "Tentar de novo" and on reload, so the timer understates the real wait; (d) metrics "Tempo: 2,4 s" vs. ~7 s of paced bubbles on screen |
| 2 | Match with real world | 4 | WhatsApp model, pt-BR register, "Afinando o atendimento" fits the brand. "guarda 0,12" is unclear even to an ML engineer ("guarda" of what?) |
| 3 | User control and freedom | 3 | The queued message can't be edited or cancelled. A selector change wipes the thread with no undo, so a misclick mid-scenario loses the test. "Sair" silently drops a queued message |
| 4 | Consistency and standards | 3 | Selector change clears the thread in chat but keeps the queued bubble in warm-up. Option B is still in 9 design files and the mockups, and screen-01 still *recommends B*. The handoff label and body repeat each other ("Confirmando com a equipe" / "Isso eu preciso confirmar com a equipe") |
| 5 | Error prevention | 3 | No guard on an accidental customer switch. "Tentar de novo" during a long wait (not a failure) re-POSTs `/warm` while the model may still be loading, which risks resetting real progress |
| 6 | Recognition over recall | 3 | Option A asks the evaluator to map "Última resposta" to a bubble from memory; earlier turns are gone. The collapsed summary shows no values, so it has to be opened every turn |
| 7 | Flexibility and efficiency | 4 | Type during warm-up is a real accelerator; Enter / Shift+Enter; password-manager autocomplete. Nothing speeds up the 4 statement scenarios, which is deliberate and fine |
| 8 | Aesthetic and minimalist | 4 | The chat is clean and store-like. The warm-up repeats the type-ahead message three times (placeholder "Pode ir escrevendo", the note, the queued line) and adds two numeric lines (expected, production) |
| 9 | Error recovery | 3 | Login errors are blame-free and specific; warm failure has retry and moves focus; send failure has "Manda de novo?". Not specified: an SSE error *after* bubble 1, `/warm/status` poll failures (network vs. `failed`), session expiry while a message is queued |
| 10 | Help and documentation | 3 | The warm-up explains itself well. The demo strip doesn't: nothing says that "Conversar como…" simulates the WhatsApp caller identity, or what "Custo" is based on for a self-hosted GPU. Login doesn't warn that a ~30 s warm-up comes next |

**Total: 33/50.**

### Focus areas

**Warm-up honesty.** The contract is excellent: the UI never advances a stage on a timer, shows "Normalmente leva cerca de {ceil10} s" instead of a countdown, and never uses "faltam". Four leaks:
1. *Pre-poll stage.* screen-02 § States says "before the first status response the first stage is shown as current". Before the first poll the client doesn't know `mode` yet, so a local or provider session can flash the GPU list (or flash a warm-up at all in `provider_api`). Fix: return `mode` + `stage` in the `/auth/login` response, or show a neutral line with no list until the first poll answers.
2. *Elapsed time is client-owned.* `startedAt` is "client clock at first poll". A reload or retry restarts at 0 s even though the GPU has been booting for 50 s. Use a backend `started_at`.
3. *`expected_seconds` source.* The brief cites 175 s today and a ≤ 30 s target. If config holds the target, "cerca de 30 s" becomes the dishonest line and the long-wait copy shows up on every cold start. It must come from measured cold starts (p75), not the goal.
4. *Long-wait retry.* Long wait ≠ failure. The primary "Tentar de novo" there invites the user to restart a container that is mid-load. Make "keep waiting" the default, and keep retry for `failed`. If retry is kept for long waits, do not reset elapsed time.

**Queued message.** Good choices: one message max, sent exactly once, Clock + words, the composer stays enabled. Issues: (a) "later sends append a new line to the same bubble" mutates a node already in `role="log"` (`aria-relevant="additions"`), so the addition is not announced; (b) the queued → sent change is silent to screen readers; (c) no undo; (d) a selector change during warm-up keeps the bubble but doesn't say who it will be sent as; (e) the message is lost on reload; (f) on mobile, scrolling to the queued bubble pushes the stage list and timer off screen.

**Sequential bubble pacing.** Backend-driven `delay_ms = clamp(400 + 22×chars, 700, 2400)`, kept under reduced motion as content timing. The idea is right. But the first bubble also waits its delay *after* the answer is ready, so 3 bubbles add up to ~7 s on top of ~2.2 s of generation. That contradicts "cada resposta sai em uns 2 s" on the warm-up screen and the "Tempo" metric. The typing indicator has already covered generation time, so the first bubble should appear at once; pace only the 2nd and 3rd, and cap added pacing at ~3 s per reply.

**HandoffBubble / ProductCard.** Both are triggered only by backend flags, which is right. Handoff is calm (no oxblood, no alert). The label repeats the body, and "já te retorno" promises a callback the demo can't deliver; the evaluator has no way to see that a handoff was *recorded*. ProductCard is honest: the badge comes only from `honest_pick`, the PIX line never stacks on a promo, prices use `tnum`. Its `<h3>` skips a heading level in the chat state.

**Demo strip (option A) for an evaluator.** The tag + selector + Métricas grouping clearly reads as "tools". Problems: the collapsed summary carries no numbers; once opened, the panel (~250 px at 360 px, because the "Tempo" row wraps to 3 lines) sits *outside* the scroll container and permanently shrinks the transcript; there is no per-turn history; the cost basis isn't explained; at 1280 px the strip content is flush left at 16 px while the transcript is a centered 672 px column, so the controls float away from the conversation.

**Mobile 360–390 px.** Measured from the mockup CSS: rail ~67 px + strip on 2 rows ~90 px + composer ~61 px ≈ 218 px of chrome. On a 360×640 Android with ~56 px of browser UI, the body gets ~366 px. The GPU warm-up panel is ~670 px tall (32 px padding, 72 px Boca, 2-line h2, ~5-line explanation, expected, 3 × 32 px stages, timer, 2 notes). Result: **status below the fold** on first paint, and worse with the keyboard open. The chat itself is fine: bubbles at 80%, 44 px targets, `dvh`, safe-area padding. Moving focus to the composer on `ready` will open the soft keyboard on Android without a user gesture, which goes against the login screen's own "focus not forced" rule.

## 4. Accessibility (summary; full audit in `accessibility-audit.md`)

- Strong: `role="log"` with appended-when-complete bubbles and sr speaker prefixes; typing `role="status"` outside the log, mounted once; a stage sentence in its own status region; the timer outside live regions; failure as the only `role="alert"`; 44 px targets; walnut focus with a cream gap on terracotta; `lang="pt-BR"`.
- Gaps: 14px interactive text (summary, link button); queued append and queued → sent not announced; ProductCard heading level; the composer has no visible label (placeholder only, acceptable for chat if STYLE documents the exception); forced focus on `ready` on touch devices.

## 5. Content quality

- Real, organic data: "1.284 de entrada · 96 de saída", "R$ 0,0042", "BRJL5544332BR", diverse customer names from Campo Grande, Dourados, Três Lagoas. No lorem, no round fakes.
- Voice: on brand ("Entra aí pra conversar com a Empório", "E-mail ou senha não bateram. Confere e tenta de novo.", "Perdi o fio da conversa aqui."). No em dashes in UI copy, no emoji.
- Fixes: "cada resposta sai em uns 2 s (normalmente 2,2 s)" says the same number twice; mockup scene 2 "No violão em si, tô aqui pra ajudar." is close to the banned "estou aqui para ajudar"; the handoff label duplicates the body; "guarda" is jargon.

## 6. Implementation quality (mockups as build reference)

- Layout: centered column is the declared archetype (fine). Strip and transcript are misaligned on desktop.
- Surfaces: tinted shadow `rgb(59 42 30 / .06)`, grain on `::before` only. Good.
- Motion: brand easing, fade 150 ms, reduced-motion kill-switch covers everything. Good.
- Responsive: the strip wraps (good), the warm-up has no mobile layout of its own (the panel just gets narrower).
- Mockup-only drift the build must not copy: Google Fonts `@import` (STYLE requires Fontsource); `Chat.scroll()` always jumps to bottom (spec: only when near the bottom, else "Novas mensagens"); `.bubble` lacks `overflow-wrap: anywhere`; login empty-submit always focuses e-mail instead of the first empty field.

## 7. Visual taste (X/75)

| # | Item | Score | Note |
|---|---|---|---|
| 1 | Typography personality | 4 | Fraunces for the moments, Source Sans in chat; restraint holds |
| 2 | Color intentionality | 5 | Neutral wood + single act accent, enforced as law |
| 3 | Spacing rhythm | 3 | Chat 8/16 is right; warm-up stacks uniform 12 px margins with no grouping |
| 4 | Shadow & depth | 3 | Tinted, used only on paper sheets; deliberately minimal |
| 5 | Motion personality | 4 | Breathing Boca + dots + fade, calm and on brand |
| 6 | Content authenticity | 4 | Authored pt-BR, real catalog numbers |
| 7 | Component individuality | 4 | Rail, honest badge and handoff label are unmistakably this brand |
| 8 | Layout confidence | 3 | Correct and safe; the warm-up is a generic stacked column |
| 9 | Visual coherence | 4 | One story across login, warm-up and chat |
| 10 | Surface texture | 4 | Paper grain + wood rail; tactile without noise |
| 11 | State completeness | 4 | Many states designed; partial-reply and poll errors missing |
| 12 | Responsive craft | 3 | Chat good; warm-up not composed for phones |
| 13 | Icon consistency | 4 | Lucide only, 1.75 non-scaling stroke |
| 14 | Image direction | 3 | Raster AI concept avatar/wordmark; dark-mode wordmark plate |
| 15 | Overall impression | 4 | "Who designed this?" on the rail and warm-up |

**Total: 55/75, Level 4 Refined.**

## 8. Consistency: option B leftovers (owner chose A)

Option B is still presented as live in:
- [screen-01-chat.md](../design/screen-01-chat.md): line 4 (`?metrics=a|b`), layout diagram lines 30–31 ("(i) = metrics option B toggle"), Components "MetricsPanel (option A or B)", SSE table rows `metrics` and `done`, the whole "§ Metrics: two options for the owner to choose" incl. "Option B" and **"Recommendation for the owner: B…"** (line 86), Interactions "Info toggle (B)".
- [design/INDEX.md](../design/INDEX.md): components column "MetricsPanel (A or B)", mockups row "metrics option A vs B toggle", and the "## Open decision for the owner" section (lines 36–38).
- [shared/component-plan.md](../design/shared/component-plan.md): MetricsPanel "used by both options"; "MetricsDetails (option A) **or** TurnMetricsToggle (option B)".
- [shared/information-architecture.md](../design/shared/information-architecture.md): "(option B) metrics toggle"; "Collapsed by default in both options".
- [shared/navigation.md](../design/shared/navigation.md), [shared/responsive.md](../design/shared/responsive.md), [shared/personas.md](../design/shared/personas.md): "(option A) or … (option B)" / "(B) stays inside the column" / "(option A or B)".
- [exports/INDEX.md](../exports/INDEX.md) line 66.
- Mockups: [index.html](../design/mockups/index.html) gallery entry "3b. Conversa, métricas opção B"; [chat.html](../design/mockups/chat.html) mockup-bar buttons "A: no topo" / "B: por resposta"; [mockup.js](../design/mockups/mockup.js) renders `.info-btn` + `.turn-metrics` per turn; [mockup.css](../design/mockups/mockup.css) `.info-btn`, `.turn-metrics`, `[data-metrics=…]` rules.

Only [STATE.md](../STATE.md) records the decision.

## Related

[prioritized-fixes.md](./prioritized-fixes.md) · [alternative-directions.md](./alternative-directions.md) · [strengths.md](./strengths.md) · `accessibility-audit.md` / `accessibility-fixes.md` (auditor)
