# Accessibility Audit: emporio-chat

> Phase: critique | Project: emporio-chat | Date: 2026-11-05 | Standard: WCAG 2.2 AA
> Inputs: design chunks (screens 01-03, shared/), HTML mockups (`design/mockups/`: chat, warmup, login, index, mockup.css, mockup.js), brand `color-system.md`, `typography.md`, patterns tokens.
> Method: static markup/CSS/JS inspection plus WCAG 2.x contrast computed with `python3 -I`. No assistive technology or browser run; behaviours marked "analytical" were derived from code and should be confirmed in a manual SR/keyboard pass. Mockup-only chrome (`.mk-bar`, `#scene`, gallery) is out of scope except where it leaks into the product markup.
> Scope note: metrics panel is **option A** (collapsed `<details>` in the demo strip). Option B is dropped; leftover B code is flagged as housekeeping (A-16).

## Summary

| Principle | Result | Notes |
|---|---|---|
| 1 Perceivable | Pass with issues | All text pairs pass (4.5:1+) in light and dark. Typing dots fail 1.4.11 (2.09:1). Reflow at 320 px passes for width; short-viewport collapse is a risk. |
| 2 Operable | Fail (conditional) | Focus is lost/yanked in 3 flows (send button, retry, ready). Targets, focus visibility, not-obscured all pass. |
| 3 Understandable | Fail (1 item) | Selector change clears the transcript and moves focus (3.2.2). Labels, errors, language, auth pass. |
| 4 Robust | Pass with issues | Names/roles/values correct. Several status messages are not exposed (4.1.3). |

Issue count: **Critical 0 | High 1 | Medium 6 | Low 9 | Total 16**. Conformance: **does not yet meet WCAG 2.2 AA** until A-01 to A-07 are fixed (A-01 is a 3.2.2 failure; A-02 to A-07 are focus/status failures in common flows). Fix steps are in [accessibility-fixes.md](./accessibility-fixes.md).

## Findings

| ID | SC | Severity | Location | Finding |
|---|---|---|---|---|
| A-01 | 3.2.2 On Input, 2.1.1 | High | `chat.html:108-114`, `mockup.js:109` (`Chat.clear`) | The `#as` `<select>` acts on `change`: it wipes the transcript, inserts a divider and moves focus to the composer, with no warning. Keyboard users changing a closed select with arrow keys trigger `change` on the first arrow press in several browsers, so they are thrown to the composer and cannot browse the other options. It is also a destructive context change without confirmation. (Analytical; matches screen-01 line 98 spec, which should change.) |
| A-02 | 4.1.3, 2.4.3 | Medium | `warmup.html:47,111,124-130` | The "Pronto pra conversar." status is written into `#stage-live`, which lives inside `#warm`; 800 ms later `#warm` is removed and `Chat.input.focus()` fires. The live region is destroyed before most screen readers speak it, and the focus move interrupts it. Focus is also pulled even if the user was elsewhere (e.g. the selector). |
| A-03 | 1.4.10 Reflow, 1.4.4 | Medium | `mockup.css:77-92` | `.app{height:100dvh}` with a non-shrinking rail + strip + composer and `.body{flex:1;min-height:0;overflow-y:auto}`. At 400% zoom / 320 CSS px the viewport is about 256 CSS px tall; rail (~66) + strip (~100-150, wraps to 3 rows) + composer (~60) leave `.body` near 0 px, so the transcript is unreachable. Width reflow itself passes (select `min-width:12rem` = 192 px fits in 288 px; rail text wraps). Analytical; verify at 320x256. |
| A-04 | 2.4.3 Focus Order | Medium | `mockup.js:39,46-51` | Activating the Send button (click/Space/Enter) clears the field, `sync()` sets `send.disabled = true` while it has focus, and focus drops to `<body>`. Spec (screen-01:108, 123) says focus stays in the composer; only Enter-in-textarea honors it. |
| A-05 | 2.4.3 Focus Order | Medium | `warmup.html:119-122,162` | "Tentar de novo" calls `start()`, which hides `#failed` / `#long` (the focused button's container). Focus is lost to `<body>` and the user must tab from the top. |
| A-06 | 4.1.3 Status Messages | Medium | `warmup.html:50-53,115` | The long-wait block ("Tá demorando mais que o normal...") is revealed by toggling `hidden` on a plain `<div>`, no `role="status"`/live container. A screen-reader user waiting on the page is never told, and never learns the retry button appeared. (`#failed` has `role="alert"` and focus moves to its button: OK.) |
| A-07 | 1.4.11 Non-text Contrast | Medium | `mockup.css:124-125,162`, `warmup.html:62-65` | Typing dots are the only visual "assistant is typing" cue. Honey `#C98A2B` on spruce `#E9D8B8` = **2.09:1** (< 3:1), and the pulse drops opacity to .35. The SR text covers screen-reader users, not low-vision sighted users. |
| A-08 | 4.1.3 Status Messages | Low | `login.html:59` | "Entrando…" is a text swap on the focused submit button plus `aria-busy`; most SRs do not announce either. Submit looks inert for SR users for ~1 s (real backend: longer, it also fires `/warm`). |
| A-09 | 1.4.11 (advisory) | Low | `mockup.css:154,64,106`; dark tokens | Not required by the SC because text carries meaning, but note: current warm-up stage bar honey/cream = 2.68:1 (also conveyed by bold + icon + SR suffix); dark user bubble `#5A4130` vs page `#1E1611` = 1.90:1; hairline `#D8C29C` vs cream = 1.58:1 and `#564337` vs dark = 1.91:1 (decorative card/divider borders). |
| A-10 | 1.3.1 Info and Relationships | Low | `chat.html:32-48,66`, `mockup.js:68`, `mockup.js:101` | (a) Demo strip (`.strip`) and `.notice` sit between `<header>` and `<main>`, outside any landmark. (b) `<form id="composer">` has no accessible name, so it is not a landmark; the composer is outside `<main>`. (c) Product card uses `<h3>` and metrics panel `<h4>` with no `<h2>`/`<h3>` ancestor (jumps from h1). (d) Warm-up stage list: current step has no `aria-current="step"` (`warmup.html:109`). |
| A-11 | 3.3.1 Error Identification | Low | `login.html:48-53` | `aria-invalid="true"` is set on both fields for every error, including "rede" (server unreachable, fields are not invalid), and is never cleared when the user edits. Error text itself is good (icon + text + `role="alert"` + `aria-describedby`). |
| A-12 | 2.2.2 Pause, Stop, Hide (advisory) | Low | `warmup.html:43`, `mockup.css:159` | `.breathe` (4 s, `infinite`) on the avatar runs automatically for the whole wait (> 5 s) with no pause. Decorative and honors reduced-motion, but 2.2.2 has no reduced-motion exemption. Typing dots are within the "essential activity" exception. |
| A-13 | 1.4.4 Resize Text (advisory) | Low | `mockup.css:37,46,59,82-83` | Body, `.small`, `.btn` and rail sizes are `px`; `typography.md` specifies rem (`1rem`, `0.875rem`). Browser zoom works, but a raised default font-size preference is ignored. Use rem in the build. |
| A-14 | 4.1.3 / 2.2.2 (advisory) | Low | `mockup.js:52,56-58,87-90`; `warmup.html:142` | Announcement volume and scroll: each turn yields, in order, own-message echo ("Você: ..."), queued note, typing status, then one announcement per bubble (2-3). Acceptable but chatty; the queued append (`bubble.append("\n"+text)`) mutates an existing bubble without the "Você:" context. `scroll()` pins to bottom on every addition, yanking users who scrolled up to read. |
| A-15 | 1.4.10 Reflow | Low | `mockup.css:101` | `.bubble` uses `white-space:pre-line` with no `overflow-wrap`; a long unbroken token (tracking URL, e-mail) can overflow the 80% bubble at 320 px. |
| A-16 | housekeeping | Low | `chat.html:16-17,133`, `mockup.js:88-94,105-108`, `mockup.css:137-138,180-181`, `index.html:36` | Dropped option B is still wired: A/B toggle, per-turn `info-btn` + `.turn-metrics` rendered in the log (hidden only by `[data-metrics="a"]` CSS; `?metrics=b` re-enables), and gallery card 3b. If shipped, hidden-by-CSS buttons are fine, but delete before build so a stray focusable button cannot enter the live log. |

## Verified passes (WCAG 2.2 AA)

| Area | SC | Evidence |
|---|---|---|
| Language | 3.1.1 | `lang="pt-BR"` on all pages. |
| Page titles | 2.4.2 | Distinct per page (note: warm-up to chat transition keeps the "Aquecimento" title; same-URL swap, minor). |
| Landmarks | 1.3.1, 2.4.1 | `header` (banner), single `main`; skip link not needed (one `main`, 3 stops before composer is short, but consider). |
| Transcript | 1.3.1, 4.1.2 | `role="log"` with `aria-label`, `tabindex=0`, `aria-relevant="additions"`; sr-only "Assistente: / Você: " prefixes; timestamps `aria-hidden`; product `<article aria-labelledby>`. Scroll container (`main.body`) is the ancestor, so arrow keys scroll from the focused log. |
| Typing status | 4.1.3 | `role="status"` mounted always, text set once per reply and cleared at the end (one announcement per reply). Warm-up `#stage-live` announces on stage change only (3 times max); elapsed counter is `aria-live="off"`. |
| Selector, details, composer | 1.3.1, 2.1.1, 4.1.2 | `<label for="as">`; native `<details>/<summary>` (keyboard, expanded state exposed; panel not live, so closed-panel updates are silent: good); textarea has `aria-label`, Enter sends, Shift+Enter newline, Send button as alternative. |
| Target size | 2.5.8 | Send, Sair, selector, summary, retry, fields all 44 px; `.meta` and `.btn-link` min 24 px. Gallery/mk-bar controls ~31 px. |
| Focus visible / not obscured | 2.4.7, 2.4.11 | Global 2 px walnut outline + 2 px offset (ring vs cream 12.50, vs spruce 9.75; dark 14.82); rail uses cream ring; primary button adds cream gap. Rail/composer are outside the scroll area, so nothing covers focus. |
| Reduced motion | 2.3.3 / 2.2.2 | `@media (prefers-reduced-motion: reduce)` kills `animation`/`transition`; dots forced to opacity 1; pacing kept (content timing). |
| Forms / auth | 1.3.5, 3.3.2, 3.3.8 | Labels, `autocomplete=username/current-password`, no paste block, no cognitive test. |
| Names | 2.5.3, 4.1.2 | Icon-only send has `aria-label`; icons `aria-hidden`; visible text matches names; decorative images `alt=""`; wordmark `alt="Empório da Música"` (logo exempt from 1.4.5). |
| Colour use | 1.4.1 | Done/current/pending stages differ by icon + weight + SR suffix; error = icon + text; honest badge = icon + text. |

## Contrast table (computed, WCAG 2.x relative luminance)

| Pair (as rendered) | Light | Dark | Requirement | Result |
|---|---|---|---|---|
| Text on page (`--foreground` / `--background`) | 12.50 | 14.82 | 4.5 | Pass |
| Text on agent bubble (`--card`) | 9.75 | 12.84 | 4.5 | Pass |
| Muted (timestamps, helper, labels, tag) on page | 6.45 | 9.21 | 4.5 | Pass |
| Muted on bubble/card; on popover (placeholder) | 5.03 ; 6.89 | 7.98 ; 7.98 | 4.5 | Pass |
| Muted on paper grain (worst case 5% multiply) | 5.90 | n/a (grain off) | 4.5 | Pass |
| Rail text / rail subtitle | 12.50 / 9.75 | 7.82 / 4.86 | 4.5 | Pass (dark subtitle margin 0.36) |
| Primary label (cream/terracotta) / hover | 5.31 / 6.41 | 5.52 / 6.97 | 4.5 | Pass |
| User bubble text | 12.50 | 7.82 | 4.5 | Pass |
| Honest chip (success on popover); success icon on page | 6.91 ; 6.47 | 7.13 ; 8.23 | 4.5 | Pass |
| Error (`--destructive`) on page / on login card | 6.88 / 5.37 | 7.53 / 6.52 | 4.5 | Pass |
| Input / textarea / select border on field | 6.89 | 3.58 (popover), 4.14 (page) | 3 | Pass |
| Focus ring on page / card (rail: dark 7.82) | 12.50 / 9.75 | 14.82 / 7.82 | 3 | Pass |
| Typing dots (honey on spruce) | **2.09** | 7.32 | 3 | **Fail light** (A-07) |
| Current-stage bar (honey on cream) | 2.68 | n/a | 3 (advisory) | Redundant cue (A-09) |
| Card/bubble vs page; hairline vs page | 1.28; 1.58 | 1.90 (user bubble); 1.91 | 3 only if sole identifier | Not required (text identifies) (A-09) |
| Disabled send (muted on spruce) | 5.03 | 7.98 | exempt | n/a |
| Mockup bar (not product) | 12.99 / 8.93 / 14.59 | | 4.5 | Pass |

Brand-doc cross-check: all values match `color-system.md` (terracotta 5.31, success 5.05 on spruce, dark action 5.52). Dark `--error/--success/--warning` are marked "pending dark audit" there; the mockup's `#FC8777` / `#9ABA7E` / `#E0A94F` pass (above), so close that note in the brand doc.

## Keyboard / focus walkthrough (analytical)

1. Chat: Sair, selector, Métricas summary, log (focusable region), textarea, Send (when enabled). Order matches visual order. Send is `disabled` when empty, so Tab skips it (acceptable; cf. A-04 for the focus loss when it becomes disabled).
2. Summary toggles with Enter/Space; panel contents are definition lists with `h4` headings.
3. Warm-up: retry buttons reachable; `#failed` focuses its retry button (good); after retry focus is lost (A-05).
4. Login: error moves focus to the e-mail field, alert text also referenced by `aria-describedby` (good); both fields `aria-invalid` (A-11).

## Recommendations beyond fixes

- Offer a "skip to message box" link or `main` landmark including the composer; consider wrapping the transcript + composer in one `<main>`.
- Run a real NVDA/VoiceOver pass on the log announcement order (A-14) and 320x256 zoom (A-03) before build sign-off.
