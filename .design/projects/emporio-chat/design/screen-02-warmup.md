# Screen 02: Warm-up (chat body state)

> Phase: design | Project: emporio-chat | Generated: 2026-11-05 | Revised: 2026-11-05 (revision 1)
> Brand: [warmup-status.md](../../../branding/emporio-da-musica/patterns/components/warmup-status.md) (adapted per [target-adaptations.md](../brief/target-adaptations.md)) · Mockup: [mockups/warmup.html](./mockups/warmup.html) (`?variant=gpu|local|api`)
> Revision 1: mobile-first order (status first at 360 × 640), Boca 48 px, one merged note, pinned one-line status once a message is queued; status and elapsed time come only from the backend (`started_at`, measured p75); poll network error separate from `failed`; no retry in the long wait; persistent live region outside the panel; focus after the announcement; queued message undo + announcements.

## Purpose

Explain the cold start honestly and keep the evaluator productive: they can type now and the message goes on its own when the model is ready. Bold Bet 3 ("Honest warm-up") is the whole screen.

## User flow position

Login success (response already carries the warm status) → `POST /warm` (fire and forget) → chat shell opens → body polls `GET /warm/status` every ~1 s → on `ready`, body becomes the transcript (screen 01) and any queued message is sent.

## Backend contract (the only source of truth)

`POST /auth/login` and `GET /warm/status` → `{ mode: "modal_gpu" | "local_cpu" | "provider_api", stage: "server_starting" | "model_loading" | "ready" | "failed", started_at, expected_seconds }`

- **First frame is right**: the login response carries the same object, so the shell renders the correct mode and stage immediately (no GPU list in `local_cpu`, no warm-up flash in `provider_api`). If that object is missing, show only the h2 + "Verificando o assistente…" with no stage list until the first poll answers. The client never invents a stage.
- **Elapsed** = `now - started_at` (backend timestamp of the first `POST /warm` of this cold start). A reload or a retry never resets it to 0 s.
- **`expected_seconds`** = measured p75 of recent cold starts for this `mode`, written to config by the deploy measurement. Never the 30 s target. Shown rounded up to 10 s.
- The UI never advances a stage on a timer.

## Layout (inside the chat shell, mobile-first, one order at every width)

```
┌ WoodRailHeader (unchanged) ─────────────┐
├ Demo strip (selector usable) ───────────┤
│  [Boca 48, md: 72]           [pegs, md+]│  max-w-md column, cream + paper grain, py-6 px-6
│  Afinando o atendimento                 │  h2, Fraunces 600, tabindex=-1 (retry focus target)
│  ✓ Ligando a GPU                        │  <ol>: done = CircleCheck moss; current = icon + 4px
│ ▌⌗ Carregando o modelo                  │        honey-deep marker + 600 + aria-current="step"
│  ○ Pronto pra conversar                 │        pending = Circle muted
│  Esperando há 12 s                      │  count-up, tnum, aria-live off
│  Normalmente leva cerca de 30 s.        │  muted, ceil10(expected_seconds)
│  Explanation (variant copy)             │
│  One merged 14px muted note             │
│  (network / long wait / failure block)  │
├ queued user bubble, if any (role=log) ──┤
├ Composer: placeholder "Pode ir escrevendo" ┤
```

At 360 × 640 (~366 px of body) the h2, the stage list, the timer and the expected line are all above the fold.

**Queued, below `md`**: once a message is queued, the panel collapses to one pinned line (`position: sticky; top: 0` inside the scroll body) so the status survives scrolling and the open keyboard: `Cpu`/`Server` 16px + "Carregando o modelo · 18 s" (600, `tnum`, `aria-hidden`, not live; the sr stage sentence in the persistent status region keeps announcing changes). The h2 stays in the accessibility tree (visually hidden). Network, long-wait and failure blocks still render under the pinned line. At `md+` the full panel stays.

## Variants

| | `modal_gpu` (hosted) | `local_cpu` (`make up PROVIDER=local`) | `provider_api` |
|---|---|---|---|
| Explanation | "O assistente roda no Gemma 4 31B, numa GPU só dele no Modal. Quando ninguém está usando, ela desliga pra não gerar custo, e ligar de novo leva um tempinho." | "O modelo está rodando na sua máquina, sem GPU. Cada resposta pode levar de 30 s a alguns minutos." | none: chat ready on arrival |
| Stages | Ligando a GPU (`Server`) → Carregando o modelo (`Cpu`) → Pronto pra conversar | Carregando o modelo → Pronto pra conversar | none |
| Expected line | "Normalmente leva cerca de {ceil10(expected_seconds)} s." | same sentence, local p75 | none |
| Merged note (14px muted) | "Com a máquina já ligada, a primeira mensagem sai em uns 2 s. Se escrever agora, a mensagem vai sozinha quando ele ficar pronto." | "Pra respostas em uns 2 s, use a versão hospedada. Se escrever agora, a mensagem vai sozinha quando ele ficar pronto." | none |
| After ready | normal chat | chat + persistent quiet notice under the strip | normal chat |

"Uns 2 s" is the first bubble on screen (bubble 1 has no pacing delay), so it matches what the evaluator times and the metrics' "no modelo" number. The type-ahead invitation lives in the placeholder ("Pode ir escrevendo"); the note only says what happens.

Timer copy: "Esperando há {s} s", after 60 s "Esperando há {m} min {ss} s". Never a countdown, never "faltam", never a percentage, never a progress bar, never a spinner.

## Components

WarmupStatus (project variant) · persistent StatusRegion (shell level) · WoodRailHeader · DemoStrip/CustomerSelector/MetricsDetails · ChatTranscript (queued bubble) · Composer · Button (retry, failed only). Boca avatar uses `ring-breathe` (one breath); tuning-peg drawing (96 px) only at `md+`.

## States

| State | Treatment |
|---|---|
| Default (warming) | stages + count-up timer from `started_at`; Boca breathes once on arrival |
| Before first status (no login payload) | h2 + "Verificando o assistente…", no stage list |
| Loading | is this screen; no skeleton, no spinner |
| Stage change | list re-renders; sr-only sentence in the persistent status region (e.g. "Carregando o modelo.") |
| Poll network error | after 3 consecutive failed polls: `WifiOff` 16px + "Não consegui falar com o servidor agora. Confere a conexão." (announced once); polling and timer continue; line removed on the next good response. Not `failed`, no retry button |
| Long wait (elapsed > 2 × rounded expected, per mode) | "Tá demorando mais que o normal. Ainda está em: {current stage}. Pode esperar, a mensagem que você escrever vai assim que ficar pronto." No button. Written once into the persistent status region; timer keeps counting |
| Error (`failed`) | timer stops; `role="alert"` with `CircleAlert` + "Não consegui ligar o assistente agora. Tenta de novo daqui a pouco." + primary "Tentar de novo" (focus moves to it). Queued message stays queued |
| Retry (failed only) | re-issues `POST /warm`; `started_at` kept (timer resumes, never 0 s); failure and long-wait blocks hidden; focus moves to the h2 (`tabindex=-1`) |
| Message queued | user bubble in the log with `Clock` 16px + "Vai assim que o assistente ficar pronto" (14px muted, part of the same appended group so it is announced once with the bubble) + link button "Desfazer" (16px). Below `md` the panel collapses to the pinned line |
| More sends while queued | each renders as a new bubble in the same group (a log addition, announced); flushed as one message joined by `\n` |
| Undo | text (all queued lines joined by `\n`) back in the composer, group removed, focus to the composer, status region: "Mensagem desfeita. O texto voltou pra caixa de mensagem." |
| Queued + reload | queued text kept in `sessionStorage` and re-rendered |
| Queued + session expiry | text kept in `sessionStorage`; after re-login it is restored into the composer (not auto-sent) |
| Ready | status region: "Pronto pra conversar."; 800 ms on the all-done list; panel removed; queued message flushed exactly once (TypingIndicator status announces activity); focus rule below |
| Selector change during warm-up | allowed, no focus move; if a message is queued, divider "Agora conversando como Ana" above it and the line becomes "Vai como Ana assim que o assistente ficar pronto" |

## Interactions

| Trigger | Response |
|---|---|
| Poll response with new stage | update list + sr sentence; no animation on the list |
| Every 1 s | timer text updates (not announced) |
| Send during warm-up | Send active; message rendered as queued, not posted to `/chat` |
| Desfazer | see Undo |
| Tentar de novo (failed) | warm-darken / settle-press; restart attempt; focus to h2 |

Only motion: `ring-breathe` (4 s, one iteration, Boca). Off under reduced motion.

## Accessibility

- Order: rail → strip → h2 → stage list → timer → expected → explanation → note → status blocks → queued bubble → composer.
- **Persistent status region**: one `role="status"` `sr-only` element mounted in the shell's `<main>`, **outside** the warm-up container, so it survives the panel's removal. It carries stage sentences, the long-wait sentence (once), the network sentence (once), undo confirmation and "Pronto pra conversar.". The `<ol aria-label="Etapas">` itself is not live.
- Each stage item has visible text plus sr-only state ("concluído", "em andamento", "a seguir"); current item `aria-current="step"`.
- Timer outside any live region. Failure is the only `role="alert"`.
- **Focus on `ready`**: wait ~2 s after writing "Pronto pra conversar." (800 ms + 1200 ms) so the announcement is spoken before any focus move. Then move focus only if focus was on `body` or inside the removed panel: to the composer when `matchMedia("(pointer: fine)")`; on touch, to the log (no soft keyboard). If the user is elsewhere (selector, Métricas, composer), focus is left alone.
- Breathing avatar `alt=""`; pegs drawing `aria-hidden`; one breath keeps it under SC 2.2.2's 5 s.
- Contrast: all text on cream from the token table (foreground 12.50, muted 6.45, success icon 6.47); current-stage marker honey deep `#8A5A14` 6.0:1.

## Responsive

360 px: panel `px-6 py-6`, Boca 48 px, no pegs; status first; pinned line once queued. ≥ 768 px: Boca 72 px, pegs drawing floats right, full panel always; column stays `max-w-md` (28 rem) centered.

## Image resources

| Section | Type | Source | Treatment |
|---|---|---|---|
| Boca | raster concept | `identity/assets/avatar-disc-concept.jpg` | circle, 48 px (72 at `md+`), one `ring-breathe` |
| Tuning pegs | line drawing | hand-built SVG (imagery-style.md spec, 96 × 96) | walnut `currentColor`, one honey-filled peg at 20% |
| Canvas | texture | `.surface-paper` grain .05 | off in dark mode and `prefers-reduced-data` |

## Related

- [screen-01-chat.md](./screen-01-chat.md) · [shared/micro-interactions.md](./shared/micro-interactions.md)
