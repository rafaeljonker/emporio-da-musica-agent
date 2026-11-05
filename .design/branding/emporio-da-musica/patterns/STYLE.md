# Style

## Brand: Empório da Música
**Style:** emporio-da-musica (brand-derived, no style_base) | **Generated:** 2026-11-05

> STYLE.md is the single document designer and builder agents consume. Rendered from [emporio-da-musica.yml](./emporio-da-musica.yml) + strategy (archetype, positioning, voice) + identity's boldest choices. Stack: Vite + React + TypeScript + Tailwind CSS v4 + shadcn/ui (Radix), lucide-react, Fontsource.

---

## Intensity

| Dial | Value | Meaning |
|------|-------|---------|
| Variance | 3 | Calm, familiar chat patterns (Sage). One editorial moment per non-chat screen: the Fraunces headline on cream |
| Motion | 2 | Near-static. Only ring breathing (warm-up), typing dots, 150ms message fade. All off under reduced motion |
| Density | 4 | Chat is compact like WhatsApp; login and warm-up are airy, few words, lots of cream |

---

## Philosophy

A conversation across a wooden counter on a Saturday morning: daylight on a pale spruce top, honey varnish, a walnut counter, one terracotta price tag. The design is the Everyperson friend who plays (70%) with a Sage's restraint (30%): it never shouts, never sells urgency, and lets real words and real numbers do the work. Warmth comes from wood tones, soft-serif Fraunces headlines and faint paper grain; clarity comes from a plain humanist sans in the chat, where nothing decorative is allowed near the text. Honesty is visual too: one color means "you can act here", the wait is explained instead of disguised, and the assistant is a soundhole, not a face.

> Heartbeat: "Conversar no balcão de madeira com quem toca há anos: sem pressa, sem empurrão, só a verdade sobre o que vai soar bem nas suas mãos."
> Tagline: "A verdade de quem toca."

---

## Tokens (summary)

Full values in the `.yml`; generate CSS with `node .claude/skills/gsp-brand-guidelines/bin/theme-css.js .design/branding/emporio-da-musica/patterns/emporio-da-musica.yml`.

| Token | Light | Dark | Role | Text pair ratio (light / dark) |
|---|---|---|---|---|
| `background` | `#FAF4EA` cream | `#1E1611` | page, chat canvas | foreground 12.50 / 14.82 |
| `foreground` | `#3B2A1E` walnut | `#F3E9D8` | all text | — |
| `card` | `#E9D8B8` spruce | `#2E221A` | cards, agent bubbles, header | 9.75 / 12.84 |
| `popover` | `#FFFCF6` paper | `#2E221A` | inputs fill, sheets, menus | 13.35 / 12.84 |
| `primary` | `#A54A29` terracotta | `#D9734C` | action only | label 5.31 (cream) / 5.52 (night) |
| `accent` | `#C98A2B` honey | `#E0A94F` | selected/active marks, menu highlight | walnut 4.66 / night 8.45 |
| `secondary`, `muted` | `#E9D8B8` | `#2E221A` | chips, quiet fills | muted-fg 5.03 / 7.98 |
| `muted-foreground` | `#6B5444` | `#C9B8A0` | timestamps, helper text | 6.45 on cream / 9.21 |
| `destructive` | `#9A2E24` oxblood | `#FC8777` | errors (icon + words) | 6.88 / 7.53 |
| `border` | `#D8C29C` grain line | `#564337` | decorative hairlines only | n/a (not a boundary) |
| `input` | `#6B5444` | `#8A7668` | form control boundary | 6.45 / 4.14 (3:1 non-text) |
| `ring` | `#3B2A1E` | `#F3E9D8` | focus | 12.50 / 14.82 |
| `success` | `#46602B` moss | `#9ABA7E` | done, confirmed | 6.47 / 8.23 |
| `warning` | `#8A5A14` honey deep | `#E0A94F` | cream/paper only in light | 5.40 / 8.45 |
| `info` | `#6B5444` | `#C9B8A0` | calm notice, never blue | 6.45 / 9.21 |

**Brand extensions** (not emitted by `theme-css.js`; add to `globals.css` and `@theme inline`):

```css
:root {
  --user-bubble: #3B2A1E;  --user-bubble-foreground: #FAF4EA;   /* 12.50 */
  --primary-hover: #93401F;                                       /* cream label 6.41 */
  --brand: #C98A2B;        --brand-text: #8A5A14;                 /* decorative / text-on-cream */
  --paper: #FFFCF6;
  --rail: #3B2A1E;  --rail-foreground: #FAF4EA;  --rail-muted: #E9D8B8;  --rail-rule: #C98A2B;  /* 12.50 / 9.75 / rule 4.66 */
}
.dark {
  --user-bubble: #5A4130;  --user-bubble-foreground: #F3E9D8;   /* 7.82 */
  --primary-hover: #E58B66;                                       /* night label 6.97 */
  --brand: #E0A94F;
  --rail: #5A4130;  --rail-foreground: #F3E9D8;  --rail-muted: #C9B8A0;  --rail-rule: #E0A94F;  /* 7.82 / 4.86 / rule 4.46 */
}
```

Type: Fraunces (display, `--font-display`) 500–600, `"SOFT" 100, "WONK" 0`; Source Sans 3 (`--font-sans`) 400/600; 16px base, 1.5 line height; Minor Third 1.200 desktop, Major Second 1.125 mobile (fluid `--text-*` vars in identity/typography.md). Radius 12px (`--radius`). Spacing on a 4px grid. Easing `cubic-bezier(0.33, 1, 0.68, 1)`.

---

## Patterns

### Card
| Property | Rule |
|----------|------|
| border | none on cream (the spruce fill separates); 1px `border` only when a card sits on spruce |
| shadow | none at rest; `shadow-sm` (walnut-tinted) for paper sheets/popovers |
| radius | `rounded-lg` (12px) |
| background | `bg-card` (spruce); faint wood grain allowed on large cards (login card), never on text-dense cards |
| padding | `p-6` mobile, `p-8` desktop |

### Button (primary)
| Property | Rule |
|----------|------|
| background | `bg-primary`; hover/pressed `--primary-hover` (#93401F) |
| border | none |
| text | Source Sans 3 600, 16px, sentence case, `text-primary-foreground` at full opacity |
| radius | `rounded-full` pill; send button is a 44px circle with a 20px `Send` icon |
| scope | one per view; terracotta never appears on non-clickable elements |

### Button (secondary)
| Property | Rule |
|----------|------|
| background | transparent on spruce, `bg-secondary` on cream |
| border | 1px `border-input` |
| text | Source Sans 3 600, 16px, sentence case, `text-foreground` |
| radius | `rounded-full` |

### Input
| Property | Rule |
|----------|------|
| border | 1px `border-input` (walnut muted, meets 3:1) |
| radius | `rounded-md` (8px); chat composer `rounded-full` |
| background | `bg-popover` (paper) |
| focus | 2px walnut outline + 2px cream offset; border unchanged |
| label | walnut label above the field (never placeholder-only); font-size 16px (no iOS zoom) |

### Badge
| Property | Rule |
|----------|------|
| shape | `rounded-full px-2.5 py-0.5`, 14px text, 16px leading icon |
| text | Source Sans 3 600, sentence case; spruce fill + walnut text |
| status | semantic text color + Lucide icon + word, never color alone; never terracotta |

### Navigation (chat header = wood rail)
| Property | Rule |
|----------|------|
| style | the **wood rail**: solid `--rail` walnut fill, `border-bottom: 3px solid var(--rail-rule)` (honey). No grain, no image |
| identity | avatar disc (`identity/assets/avatar-disc-concept.jpg`) + "Assistente da Empório" in `--rail-foreground` (12.50) + subline "assistente virtual da loja" in `--rail-muted` (9.75; dark 4.86) |
| focus | cream ring (`--rail-foreground`, 12.50) inside the rail; walnut ring would vanish |
| links | walnut, underline offset 3px; terracotta text links only on cream (4.52), `#93401F` on spruce (5.00) |

### Layout
| Property | Rule |
|----------|------|
| archetype | **centered** (single chat column, mobile-first) |
| max-width | `max-w-2xl` chat column; `max-w-md` login/warm-up card; `60ch` prose |
| section-spacing | chat: 8px between same-sender bubbles, 16px on speaker change; screens `py-12`–`py-16` |
| grid-gap | `gap-4` to `gap-6` |
| surfaces | paper grain on the cream canvas (.05), wood grain on spruce header/login card; flat fills on bubbles, inputs, buttons |
| decoration | one walnut line drawing per screen (tuning pegs on warm-up, rosette on empty chat); soundhole-rosette tile at 4% on login/warm-up canvas |

### Chat bubbles (brand-specific)
| Element | Rule |
|---------|------|
| agent | `bg-card text-card-foreground`, `rounded-2xl` with `rounded-bl-md` on the first bubble of a group; avatar once per group |
| user | `bg-[--user-bubble] text-[--user-bubble-foreground]`, right-aligned, `rounded-2xl rounded-br-md` |
| content | Source Sans 3 400 16/24, plain text only (no markdown); max width ~80% |
| typing | spruce bubble, three 6px honey dots; `sr-only` "O assistente está digitando" |
| timestamp | 13px `text-muted-foreground`, tabular figures |
| handoff | see below |

### Bubble: handoff / limit admitted (Sage "truth")
| Property | Rule |
|----------|------|
| use | the agent does not know or must confirm a fact; calm, not an error |
| container | the normal agent bubble (spruce/walnut); no border, tint or shake |
| label | first line in the bubble: Lucide `UserRound` (or `Clock` when a return time is promised) 16px + "Repassado pra equipe", 14px 600 `text-muted-foreground` (5.03 on spruce) |
| copy | "Isso eu preciso confirmar com a equipe. Já deixei registrado pra eles." |
| a11y | label is visible text; announced like any message, no `role="alert"` |
| never | terracotta (not clickable), oxblood / `CircleAlert` (not an error), honey fill, spinner |

### Product card in chat (cheaper option + price block)
| Property | Rule |
|----------|------|
| container | `bg-popover` (paper), `rounded-lg`, 1px `border` hairline + `shadow-sm`, `p-4`, max 80% wide, inside the agent group |
| name | Source Sans 3 600 16px walnut (13.35 on paper) |
| honest badge | `CircleCheck` 16px + "Na medida pro seu nível", 14px 600 `text-success` moss on paper (6.91), 1px `border` hairline, `rounded-full` |
| price | final price 600 20px tabular; PIX line 14px `text-muted-foreground` (6.89 on paper) |
| promotion | one line, three parts: "De R$ 2.399" muted + line-through (the word "De" carries meaning) · "18% off" 600 `text-warning` honey deep (5.77 on paper) · "R$ 1.967,18" 600 walnut. PIX 5% never stacks on promo |
| never | terracotta badge or price, red sale banner, honey deep on spruce (4.22), a discount without the original |

---

## Constraints

### Never
- Terracotta on anything that is not clickable — if it is terracotta and not an action, it is a bug.
- Blue or cool grey anywhere, including links and info states — breaks the wood palette.
- Cream text on honey (2.68) or a cream label on dark-mode terracotta (2.68) — fails AA.
- Honey `#C98A2B` as text on any light surface; honey deep `#8A5A14` as text on spruce (4.22).
- Terracotta `#A54A29` as text on spruce (3.53) — use `#93401F` (5.00).
- Fraunces in chat bubbles, buttons, labels, prices or timestamps — chat must read like WhatsApp, not a letter.
- ALL CAPS headings or labels; a third typeface; script or handwriting fonts.
- Markdown in chat bubbles (bold, lists, headers).
- Emoji in UI copy; robot, sparkle or AI icons for the assistant; a face on the avatar.
- Spinners, progress bars or fake percentages on the warm-up screen; rotating the logo.
- Texture behind chat bubbles, inputs, buttons or any text under 18px.
- Gradients across large surfaces; red sale banners; black-and-gold pairing; pure black.
- Body or interactive text under 16px (13–14px only for non-interactive metadata).

### Always
- Terracotta for the single primary action per view; cream label at full opacity.
- Walnut 2px focus ring with 2px cream offset on every focusable element.
- Semantic states carry icon + words (`CircleCheck` moss, `CircleAlert` oxblood).
- Agent bubbles spruce/walnut, user bubbles walnut/cream; avatar once per agent group.
- Tabular figures on the warm-up timer and every price in UI.
- Sentence case; pt-BR copy per strategy/voice-and-tone.md; "Empório" always with the accent.
- Lucide outline icons, `strokeWidth={1.75}` + `absoluteStrokeWidth`; pt-BR `aria-label` on icon-only buttons.
- Honor `prefers-reduced-motion` (no animation) and `prefers-reduced-data` (no grain); the wood rail is solid color and stays.
- The wood rail on every chat screen: walnut header + 3px honey bottom rule.
- Unknown fact = handoff bubble (walnut-muted label + `UserRound`/`Clock`), never a guess and never error styling.
- When the cheaper instrument fits, say so with the honest badge; promotions show original + % + final.
- Self-hosted fonts via Fontsource, latin + latin-ext subsets only.

---

## Effects

**Interaction vocabulary:** warm-darken, settle-press, fade-arrive, ring-breathe, dot-pulse

### Hover
| Element | Technique | Description |
|---------|-----------|-------------|
| card | none | cards are not interactive; selectable rows (customer selector) show a 4px honey left marker |
| button | warm-darken | primary `#A54A29` → `#93401F`; secondary gains spruce fill |
| link | underline-thicken | 1px → 2px underline, color unchanged |

### Active
| Element | Technique | Description |
|---------|-----------|-------------|
| button | settle-press | `#93401F` + `scale-[0.98]`, 100ms |

### Focus
| Element | Rule |
|---------|------|
| general | `outline-2 outline-ring outline-offset-2` (offset shows the cream/spruce behind) |
| primary button | add `box-shadow: 0 0 0 2px var(--background)` under the outline so walnut never touches terracotta (2.76) |

### Transition
150ms `cubic-bezier(0.33, 1, 0.68, 1)` for color and opacity; no layout animation.

### Ambient
- ring-breathe — Boca icon scale 1 → 1.04, opacity → .85, 4s ease-in-out, warm-up only.
- dot-pulse — three honey typing dots, staggered opacity pulse, 1.2s.
- fade-arrive — each new bubble fades in and rises 4px, 150ms; bubbles of one reply arrive sequentially.

### Surfaces
- wood-rail — chat header `background: var(--rail); border-bottom: 3px solid var(--rail-rule)`. Solid colors only, so it survives `prefers-reduced-data` and dark mode, and no texture ever sits behind its text. Static. Intensity dials unchanged (variance 3, motion 2, density 4).

---

## Bold Bets

1. **One color means "act".** Terracotta exists only on clickable elements (CTA, send, retry). No badge, banner, icon or illustration may use it. Review rule: any non-interactive terracotta pixel is a bug.
2. **Boca avatar.** The assistant is the soundhole "ó" on a honey disc (`identity/assets/avatar-disc-concept.jpg`; favicon `favicon-concept.jpg`; wordmark `logo-wordmark-concept.jpg`), never a face or a robot. **The logo is a raster AI-generated concept pending vectorization** (SVG, colors locked to brand tokens, Fraunces outlines; see identity/logo-directions.md, Decision 2026-11-05). `boca-icon*.svg` are construction references only. It is the only thing that moves on the warm-up screen, breathing slowly.
3. **Honest warm-up.** "Afinando o atendimento" in Fraunces, a plain explanation, three named stages with icons (`Server`, `Cpu`, `CircleCheck`; pending `Circle`), and a real elapsed timer in tabular figures. No progress bar, no percentage, no spinner. Stage changes go to a polite live region; the timer is not announced each second.
4. **Wood-on-paper surfaces.** Cream canvas with SVG paper grain at .05, login card with faint wood bands, and the chat's solid walnut wood rail with a honey rule (the one wood cue that never switches off), all on `::before` pseudo-elements so text layers stay flat and contrast never moves.
5. **Walnut user bubbles.** The customer's words sit on the dark wood of the counter (walnut, cream text); the store's words sit on spruce. Speaker is obvious on a small screen without color-only cues.

---

## Implementation

### Component Code Hints

```css
/* globals.css (Tailwind v4) — after the theme-css.js :root/.dark block + brand extensions */
@theme inline {
  --color-user-bubble: var(--user-bubble);
  --color-user-bubble-foreground: var(--user-bubble-foreground);
  --color-primary-hover: var(--primary-hover);
  --color-brand: var(--brand);
  --color-brand-text: var(--brand-text);
  --color-paper: var(--paper);
  --color-success: var(--success);
  --color-warning: var(--warning);
  --color-info: var(--info);
  --font-display: "Fraunces", Georgia, "Times New Roman", serif;
  --font-sans: "Source Sans 3", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
```

```tsx
// Primary (shadcn Button variant="default")
"rounded-full bg-primary text-primary-foreground font-semibold h-11 px-6 hover:bg-primary-hover active:scale-[0.98] transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2 focus-visible:shadow-[0_0_0_2px_var(--background)]"
// Secondary
"rounded-full border border-input bg-secondary text-foreground font-semibold h-11 px-6"
// Input
"h-11 rounded-md border border-input bg-popover px-3 text-base text-foreground placeholder:text-muted-foreground"
// Agent bubble / user bubble
"max-w-[80%] rounded-2xl rounded-bl-md bg-card px-4 py-2.5 text-base text-card-foreground"
"ml-auto max-w-[80%] rounded-2xl rounded-br-md bg-user-bubble px-4 py-2.5 text-base text-user-bubble-foreground"
// Send (icon-only)
<Button size="icon" className="size-11 rounded-full" aria-label="Enviar mensagem"><Send size={20} strokeWidth={1.75} absoluteStrokeWidth aria-hidden /></Button>
// Chat header (wood rail) — also add --color-rail* to @theme inline
"flex items-center gap-3 px-4 py-3 bg-rail text-rail-foreground border-b-[3px] border-rail-rule [&_:focus-visible]:outline-rail-foreground"
// Handoff bubble label (first line inside the agent bubble)
<span className="flex items-center gap-1.5 text-sm font-semibold text-muted-foreground"><UserRound size={16} strokeWidth={1.75} absoluteStrokeWidth aria-hidden />Repassado pra equipe</span>
// Promo price line (product card, paper)
<p className="tnum"><span className="text-muted-foreground line-through">De R$ 2.399</span> <span className="font-semibold text-warning">18% off</span> <span className="font-semibold text-foreground">R$ 1.967,18</span></p>
// Error line
<p role="alert" className="flex gap-2 text-destructive"><CircleAlert size={20} strokeWidth={1.75} absoluteStrokeWidth aria-hidden />E-mail ou senha não bateram. Confere e tenta de novo.</p>
```

shadcn's default destructive button uses `text-white`; override to `text-primary-foreground` so dark mode (`#FC8777`) gets the night label (7.53).

### Textures & Surfaces

```css
:root {
  --grain-paper: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 .23  0 0 0 0 .16  0 0 0 0 .12  0 0 0 .5 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  --grain-wood:
    repeating-linear-gradient(92deg, rgb(59 42 30 / .035) 0 1px, transparent 1px 7px),
    repeating-linear-gradient(88deg, rgb(59 42 30 / .025) 0 2px, transparent 2px 19px);
}
.dark { --grain-wood: repeating-linear-gradient(92deg, rgb(243 233 216 / .03) 0 1px, transparent 1px 7px); }
.surface-paper, .surface-wood { position: relative; isolation: isolate; }
.surface-paper::before, .surface-wood::before { content: ""; position: absolute; inset: 0; z-index: -1; pointer-events: none; }
.surface-paper::before { background: var(--grain-paper); opacity: .05; mix-blend-mode: multiply; }
.surface-wood::before  { background: var(--grain-wood); }
.dark .surface-paper::before { display: none; }
@media (prefers-reduced-data: reduce) { .surface-paper::before, .surface-wood::before { display: none; } }
```

Apply only to large containers (body/canvas, header, login card, warm-up canvas). Re-run contrast if grain opacity exceeds .06.

### Typography Treatments

```css
.font-display { font-family: var(--font-display); font-variation-settings: "SOFT" 100, "WONK" 0; font-optical-sizing: auto; letter-spacing: -0.025em; }
.tagline { font-family: var(--font-display); font-style: italic; font-weight: 400; color: var(--muted-foreground); } /* once per screen */
.tnum { font-variant-numeric: tabular-nums; }
```

Load: `@fontsource/source-sans-3` (latin + latin-ext, 400/600, preloaded) and `@fontsource-variable/fraunces` (latin + latin-ext via `unicode-range`, lazy, `font-display: swap`). No Google Fonts in the app.

### Animation Recipes

```css
@keyframes breathe { 50% { transform: scale(1.04); opacity: .85; } }
.breathe { animation: breathe 4s ease-in-out infinite; transform-origin: center; }

@keyframes dot { 0%, 80%, 100% { opacity: .35; } 40% { opacity: 1; } }
.typing-dot { width: 6px; height: 6px; border-radius: 9999px; background: var(--brand); animation: dot 1.2s infinite; }
.typing-dot:nth-child(2) { animation-delay: .15s; } .typing-dot:nth-child(3) { animation-delay: .3s; }

@keyframes arrive { from { opacity: 0; transform: translateY(4px); } }
.fade-in { animation: arrive 150ms cubic-bezier(0.33, 1, 0.68, 1); }

@media (prefers-reduced-motion: reduce) {
  .breathe, .typing-dot, .fade-in { animation: none !important; transition: none !important; }
  .typing-dot { opacity: 1; }
}
```

---

## Related

- [emporio-da-musica.yml](./emporio-da-musica.yml) — Source of truth (tokens, intensity, patterns, constraints, effects)
- [guidelines.html](./guidelines.html) — Visual brand guide
- [../identity/color-system.md](../identity/color-system.md) — Contrast audit
- [../REFINE-LOG.md](../REFINE-LOG.md) — Refinement history
- [../strategy/voice-and-tone.md](../strategy/voice-and-tone.md) — Copy rules (pt-BR)
