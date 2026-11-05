# Accessibility Fixes: emporio-chat

> Companion to [accessibility-audit.md](./accessibility-audit.md). Ordered by severity. Apply to the design chunks first, then the mockups, then the build (`frontend/`, shadcn).

## High

### A-01 | SC 3.2.2 / 2.1.1 | `chat.html:108-114`, `mockup.js:109`, screen-01-chat.md:98,123
Selector must not change context on `change`.
- Make `#as` a pure choice and add an explicit "Trocar" (apply) button next to it (44 px, `btn-secondary`). Only the button clears the thread, adds the divider and focuses the composer.
- If the instant-apply behaviour is kept for the demo: do not move focus (`Chat.input.focus()` removed), keep the thread, and only append the divider; announce via the log (already the case). Document the choice in screen-01 ("Customer switched" row).
- Update screen-01 line 123 ("after selector change ... focus is in the composer") to match.

## Medium

### A-02 | SC 4.1.3, 2.4.3 | `warmup.html:47,111,124-130`
- Move `<div id="stage-live" role="status" class="sr-only">` out of `#warm` (e.g. just inside `<main>`), so it survives removal.
- Keep `"Pronto pra conversar."` in it and delay `#warm.remove()` plus the focus call (`await sleep(2000)`), or skip the programmatic focus when `document.activeElement` is not `body`/inside `#warm`.
- Build: persistent `<StatusRegion>` in the layout; never unmount the live region with the content it announces.

### A-03 | SC 1.4.10 / 1.4.4 | `mockup.css:77-92`
- Give the transcript a floor: `.body { min-height: 12rem; }` and let the page scroll when the stack exceeds the viewport: `@media (max-height: 480px) { .app { height: auto; min-height: 100dvh; } .rail { position: static; } }`.
- Alternative: collapse `.strip` into the `<details>` below that height. Re-test at 320 x 256 CSS px.

### A-04 | SC 2.4.3 | `mockup.js:46-51`
- In `submit()`, after clearing: `this.input.focus();`. Or, keep Send always focusable: replace `disabled` with `aria-disabled="true"` and ignore clicks while empty/busy.
- Build: same rule on the shadcn `Button size="icon"`; test "Space on Send keeps focus".

### A-05 | SC 2.4.3 | `warmup.html:119-122,162`
- Add `id="warm-title"` focus target: `<h2 id="warm-title" tabindex="-1">` and in the retry handler call `$("#warm-title").focus()` after `start()`. (Or focus `#stages`.) Also hide `#long` explicitly in `start()`.

### A-06 | SC 4.1.3 | `warmup.html:50-53,115`
- Wrap long-wait copy in a persistent live container: `<div id="long-live" role="status"><div id="long" hidden>...</div></div>` (container always in DOM, content toggled), or write the sentence into `#stage-live` when `t` crosses the threshold, once.
- Build: `WarmupStatus` long-wait block renders inside the persistent status region.

### A-07 | SC 1.4.11 | `mockup.css:124`
- Light mode: `.typing-dot { background: var(--muted-foreground); }` (#6B5444 on #E9D8B8 = 5.03:1) and raise trough opacity to `.5`; keep honey only for decoration (avatar/rail rule). Dark honey `#E0A94F` already passes (7.32).
- Update `typing-indicator.md` token note: "dots use muted walnut in light, lighter honey in dark".

## Low

### A-08 | SC 4.1.3 | `login.html:59`
Add `<p id="login-live" role="status" class="sr-only"></p>`; set it to "Entrando…" on submit and clear on fail. Keep `aria-busy`.

### A-09 | SC 1.4.11 advisory | `mockup.css:64,106,154`
Optional hardening: current-stage bar to `--warning` `#8A5A14` (6.0:1 on cream); dark card/bubble edges `#7A6455` (>= 3:1) only if boundaries must identify the component. No change needed for conformance.

### A-10 | SC 1.3.1 | `chat.html:32-48,66`, `mockup.js:68,101`, `warmup.html:109`
- Wrap strip + notice in `<aside aria-label="Demonstração">` (or move inside `<main>` above the log). Give the composer `<form aria-label="Enviar mensagem">`.
- Product card title `h3` to `<p class="h3">` or `h2`; metrics headings `h4` to `<p><strong>` (or keep under an `h2`). Pick one heading model in `information-architecture.md`.
- `<li class="current" aria-current="step">`.

### A-11 | SC 3.3.1 | `login.html:48-53`
Set `aria-invalid` only for credential/empty errors (not "rede"); clear it on `input`. Keep `role="alert"` + `aria-describedby`.

### A-12 | SC 2.2.2 | `warmup.html:43`, `mockup.css:159`
Drop `.breathe` (the stage list and elapsed counter already show activity) or stop it after 5 s (`animation-iteration-count: 1`, ~5 pulses at 4 s = limit; use 1 pulse). Dots may stay (essential).

### A-13 | SC 1.4.4 | `mockup.css:37,46,59`
Use `1rem`, `0.875rem`, `0.8125rem` per `typography.md` tokens (`--text-body/-sm/-xs`); express 44 px targets as `2.75rem`.

### A-14 | SC 4.1.3 / 2.2.2 | `mockup.js:52,56-58,87-90`, `warmup.html:142`
- Mark own-message echo `aria-hidden` is not recommended (loses transcript); instead keep it and confirm in an SR pass. Merge "queued" note into the bubble's sr-only text so only one announcement occurs.
- `scroll()`: only pin when within ~80 px of the bottom (`nearBottom = b.scrollHeight - b.scrollTop - b.clientHeight < 80`).
- Queued append: append as a new `<span class="sr-only">Você: </span>` + text line.

### A-15 | SC 1.4.10 | `mockup.css:101,115`
Add `overflow-wrap: anywhere;` to `.bubble` and `.product`.

### A-16 | housekeeping | `chat.html:16-17,133`, `mockup.js:88-94,105-108`, `mockup.css:137-138,180-181`, `index.html:36`
Delete option B: toggle buttons, `.info-btn`/`.turn-metrics` markup, `[data-metrics]` rules, gallery card 3b, and `screen-01-chat.md:81` per-turn button text. Leaves one metrics surface (the `<details>`).

## Verification checklist (after fixes)
1. Keyboard only: change selector with arrows (focus stays), send via Space on Send (focus stays), retry (focus lands on heading).
2. VoiceOver/NVDA: warm-up ready announcement, long-wait announcement, one typing announcement per reply.
3. 320 x 256 CSS px (400% zoom): transcript reachable; long token wraps.
4. `prefers-reduced-motion`, light and dark: dots visible, no fade; re-run contrast script for the dot colour.
