# Responsive

> Phase: design | Project: emporio-chat | Generated: 2026-11-05 | Mobile-first: 360 px → 1280 px

| Breakpoint | Login | Warm-up body | Chat |
|---|---|---|---|
| **Mobile 360–639** (base) | column `px-4`, wordmark ~250 px, card `p-6`, top-aligned | panel `px-6 py-6`, Boca 48 px, no pegs; status first (h2 → stages → timer → expected); pinned one-line status once a message is queued | strip wraps (tag + label, selector, Métricas); open metrics panel `max-h-[40dvh]` scrolls; bubbles max 80%; composer full width |
| **Tablet 640–1023** (`sm`, `md`) | card `p-8` at `md`, column centered vertically | Boca 72 px, pegs drawing appears at `md`; full panel even when queued | strip on 1 row; transcript column grows to `max-w-2xl` |
| **Desktop 1024–1280+** (`lg`) | unchanged (`max-w-md` centered on cream) | unchanged (`max-w-md`) | rail, strip, transcript, typing and composer **content** share one 672 px centered column; rail and strip backgrounds span full width; open metrics panel spans the strip column |

## Rules

- Shell height `h-dvh`; only the transcript scrolls. Rail sticky with `env(safe-area-inset-top)`; composer padding `env(safe-area-inset-bottom)`.
- No horizontal scroll at 360 px; long tokens (tracking codes) wrap with `overflow-wrap: anywhere` inside bubbles.
- Type: Major Second (1.125) on mobile, Minor Third (1.200) on desktop via brand fluid vars; body stays 16 px everywhere (no iOS zoom).
- Targets ≥ 44 px at every width.
- 200% zoom / 320 CSS px reflow: strip and composer wrap, nothing clipped (WCAG 1.4.10).
- Short viewports (`max-height: 480px`, incl. 400% zoom ≈ 320 × 256): transcript has a `12rem` floor, the shell becomes `h-auto min-h-dvh` and the rail `static`, so the page scrolls instead of collapsing the transcript.
- Type in `rem` (`--text-body` 1rem, `--text-sm` .875rem, `--text-xs` .8125rem); targets as `2.75rem`, so a raised default font size is honored.
- Dark mode by `prefers-color-scheme` (class `.dark` in build); paper grain off in dark.

## Related
- [navigation.md](./navigation.md) · mockups: [../mockups/index.html](../mockups/index.html) (390 × 844 and 1280 × 800 side by side)
