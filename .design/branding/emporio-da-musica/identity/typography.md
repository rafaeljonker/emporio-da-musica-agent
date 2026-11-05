# Typography

> Phase: identity | Brand: emporio-da-musica | Generated: 2026-11-05

---

## Pairing

**Fraunces (headings, brand moments) + Source Sans 3 (body, UI, chat).**

Both are licensed under the **SIL Open Font License 1.1** (Fraunces by Undercase Type; Source Sans 3 by Adobe), free to use, embed and self-host. This satisfies the BRIEF's open-license non-negotiable. Both cover the full Latin set needed for pt-BR (ã, õ, ç, á, é, ê, ó, ú, and "R$").

## Primary (display): Fraunces

**Why:** the voice is *descontraída, musical, curiosa* on an honest base. Fraunces is a "soft serif": old-style bones (Sage, a store that has been around since 2008) with rounded, slightly chubby terminals (Everyperson, friendly, never posh). It feels like a hand-painted shop sign, not a luxury boutique. It is also the logo's typeface, so headings and the mark speak with one voice.

**Character settings (direction):**
- Use the variable font's **SOFT axis high** for the rounded, warm look.
- **WONK off** in UI headings (keep it calm); WONK may be allowed only in the logo and large one-off brand lines.
- Let the optical-size axis follow the rendered size.

**Weights:** 500–600 for headings. Avoid 800–900 (shouty, sale-like) and 100–300 (thin luxury minimalism, an anti-pattern).

**Use for:** login title ("Entra aí pra conversar com a Empório"), warm-up headline ("Afinando o atendimento"), tagline "A verdade de quem toca.", empty-state headline, the wordmark.

**Never use for:** chat bubbles, buttons, form labels, prices, timestamps. Chat must read like WhatsApp, and a serif in bubbles would feel like a letter, not a conversation.

## Secondary (text/UI): Source Sans 3

**Why:** humanist sans, open apertures, very legible at small sizes on cheap Android screens, neutral enough to disappear in a chat, warm enough not to feel corporate. It is the plain-spoken Nubank-clarity half of the personality reference.

**Weights:** 400 regular for all chat and body text; 600 semibold for buttons, the customer name in the selector, and the price figure when shown in UI; 700 sparingly (none needed in chat, since chat forbids markdown bold).

**Use for:** chat bubbles, inputs, buttons, labels, the "conversar como…" selector, warm-up stage list and elapsed time, error messages, timestamps.

**Numerals:** use **tabular figures** for the warm-up elapsed timer (so "38 s" → "39 s" does not jitter) and for any prices in UI components.

## Scale Direction

- **Chat: compact and close.** Bubbles feel like a messaging app: one body size, tight vertical rhythm between bubbles from the same sender, more space when the speaker changes. Body text never below 16 px on mobile (readability, and it prevents iOS input zoom).
- **Login and warm-up: airy and editorial.** Few words, one big Fraunces headline, lots of cream around it. A calm Saturday morning, not a dashboard.
- **Ratio:** moderate. Only 3–4 heading levels are needed in the whole product; the jump from body to the warm-up headline is the largest moment.
- Line length for any paragraph outside chat (warm-up explanation): roughly 45–65 characters.

Exact values are in the sections below (added by `/gsp-typography --enrich`).

## Type Scale (enriched)

Base **16px** (1rem), mobile-first. Desktop ratio **Minor Third 1.200**; mobile steps down to **Major Second 1.125** (the skill's step-down map). `size = 16 * ratio^n`, rounded to 0.5px. Only Display and H1-H3 appear in the product; H4 is spare. Chat uses `body` only.

| Level | Exp | Mobile px | Desktop px | rem (m / d) | Line height (unitless) | Tracking | Family / weight |
|---|---|---|---|---|---|---|---|
| Display | 5 | 29 | 40 | 1.813 / 2.5 | 1.1 (44px max) | -0.025em | Fraunces 600 |
| H1 | 4 | 25.5 | 33 | 1.594 / 2.063 | 1.15 (40px) | -0.025em | Fraunces 600 |
| H2 | 3 | 23 | 27.5 | 1.438 / 1.719 | 1.2 (36px) | -0.025em | Fraunces 500 |
| H3 | 2 | 20 | 23 | 1.25 / 1.438 | 1.25 (32px) | -0.015em | Fraunces 500 |
| H4 | 1 | 18 | 19 | 1.125 / 1.188 | 1.3 (28px) | -0.01em | Source Sans 3 600 |
| body-large | 0.5 | 17 | 17.5 | 1.063 / 1.094 | 1.5 | 0 | Source Sans 3 400 |
| **body (chat, inputs, buttons)** | 0 | **16** | **16** | 1 | 1.5 (24px) | 0 | Source Sans 3 400 / 600 |
| body-small | -1 | 14 | 14 | 0.875 | 1.5 | 0.01em | Source Sans 3 400 |
| caption | -2 | 13 | 13 | 0.8125 | 1.4 | 0.015em | Source Sans 3 400 |

- **16px floor:** everything a user reads or taps in chat (bubbles, inputs, buttons, selector, warm-up stages, errors) uses `body` (16px) or larger. `body-small`/`caption` are for non-interactive metadata only (timestamps, helper text), never inputs (iOS zooms inputs under 16px).
- No `overline` level: ALL CAPS is banned (see Rules).
- Line heights are unitless so they scale with fluid sizes; px values are the desktop maxima, snapped to the 4px grid.
- Fraunces: `font-variation-settings: "SOFT" 100, "WONK" 0;` and `font-optical-sizing: auto` (opsz follows size). Tagline italic: Fraunces Italic 400-500, once per screen.
- Source Sans 3: `font-variant-numeric: tabular-nums` on the warm-up timer and prices (`.tnum`).

## Fluid Type (headings only)

Interpolates between 375px and 1280px viewports; min/max are rem so browser zoom works (WCAG 1.4.4). Body and below stay fixed.

```css
:root {
  --text-display: clamp(1.8125rem, 1.5276rem + 1.2155vw, 2.5rem);
  --text-h1: clamp(1.5938rem, 1.3995rem + 0.8287vw, 2.0625rem);
  --text-h2: clamp(1.4375rem, 1.321rem + 0.4972vw, 1.7188rem);
  --text-h3: clamp(1.25rem, 1.1723rem + 0.3315vw, 1.4375rem);
  --text-h4: clamp(1.125rem, 1.0991rem + 0.1105vw, 1.1875rem);
  --text-body-lg: 1.0625rem;
  --text-body: 1rem;
  --text-sm: 0.875rem;
  --text-xs: 0.8125rem;
}
```

## Vertical Rhythm

Base line-height 24px (1.5 x 16) on a 4px grid; spacing multiples of 4px, with 8px between same-sender bubbles, 16px when the speaker changes, and headings snapped to 4px multiples (table above). Measure for non-chat paragraphs: `max-width: 60ch`.

## Font Loading (self-hosted, Vite + React)

No Google Fonts / CDN. Install via Fontsource (both SIL OFL 1.1):

```bash
npm i @fontsource-variable/fraunces @fontsource/source-sans-3
```

```ts
// main.tsx: Source Sans 3 static 400 + 600, latin + latin-ext only (pt-BR accents)
import "@fontsource/source-sans-3/latin-400.css";
import "@fontsource/source-sans-3/latin-ext-400.css";
import "@fontsource/source-sans-3/latin-600.css";
import "@fontsource/source-sans-3/latin-ext-600.css";
// Fraunces: variable (wght, opsz, SOFT; WONK unused) + italic for the tagline.
// Import ONLY the latin / latin-ext files via @font-face (below) instead of the
// package-wide full.css, which pulls every subset (cyrillic, vietnamese...).
```

```css
/* fraunces.css: confirm exact filenames in node_modules/@fontsource-variable/fraunces/files/ */
@font-face {
  font-family: "Fraunces"; font-style: normal; font-weight: 500 600; font-display: swap;
  src: url("@fontsource-variable/fraunces/files/fraunces-latin-full-normal.woff2") format("woff2-variations");
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+20AC, U+2122;
}
/* repeat for latin-ext (U+0100-02BA, U+1E00-1EFF, U+20A0-20CF) and for italic */

:root {
  --font-display: "Fraunces", Georgia, "Times New Roman", serif;
  --font-sans: "Source Sans 3", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
body { font: 400 var(--text-body)/1.5 var(--font-sans); }
```

- **Critical path:** chat is Source Sans 3 only. Preload `source-sans-3-latin-400-normal.woff2` and `-600-` in `index.html`; Fraunces appears only on login/warm-up, so load it lazily (not preloaded) and let it `swap`.
- `font-display: swap` on all faces; fallbacks (Georgia / system-ui) are close in metrics. Optionally tune `size-adjust` on a fallback `@font-face` to limit shift.
- Budget: ~2 Source Sans weights x 2 subsets + Fraunces variable roman (+ italic) latin; latin-ext files download only when an accent outside latin is needed (unicode-range).
- Tailwind v4: map tokens with `@theme { --font-display: ...; --font-sans: ...; --text-h1: ...; }`.

## Rules

- Sentence case everywhere. No ALL CAPS headings (they shout); small tracked caps allowed only for "da Música" in the logo lockup.
- Italic Fraunces may be used once per screen for warmth (e.g., the tagline), never for emphasis in chat.
- No third typeface. No script or handwriting font, even for the "price tag" feel; warmth comes from Fraunces's soft terminals.
- Self-host both fonts (no third-party font CDN tracking) and subset to Latin + Latin Extended.

## Related

- [Logo Directions](./logo-directions.md)
- [Color System](./color-system.md)
- [Brand Applications](./brand-applications.md)
