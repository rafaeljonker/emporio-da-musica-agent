# Token Mapping — Empório da Música → shadcn/ui on Tailwind CSS v4

> Phase: patterns (Pass 2) | Brand: emporio-da-musica | Generated: 2026-11-05
> Source of truth: [../emporio-da-musica.yml](../emporio-da-musica.yml). Contract: [../STYLE.md](../STYLE.md).
> Stack: Vite + React + TypeScript, Tailwind CSS v4 (CSS-first), shadcn/ui (Radix), lucide-react, Fontsource. Strategy: `generate` (greenfield, `frontend/`).

Token names in the `.yml` are 1:1 with shadcn/ui CSS variable names. No translation layer.

---

## 1. How the CSS is produced

| Layer | Produced by | Where it lands |
|---|---|---|
| shadcn core vars (`:root` / `.dark`): background … chart-5, `--radius`, fonts, `--success/--warning/--info` | `theme-css.js` from the `.yml` (OKLCH), packaged as [../emporio-da-musica.theme.json](../emporio-da-musica.theme.json) (`registry:theme`) | `frontend/src/index.css` via `/gsp-brand-apply` (do not hand-paste) |
| Brand extensions (user bubble, primary hover, honey, paper, wood rail) | Hand-written, Section 4 below | Same file, directly after the generated block |
| `@theme inline` bridge (vars → Tailwind utilities) | Hand-written, Section 5 below | Same file |

Regenerate the core block after any `.yml` change:

```bash
node .claude/skills/gsp-brand-guidelines/bin/theme-css.js .design/branding/emporio-da-musica/patterns/emporio-da-musica.yml
```

Dark mode is class-based (`.dark` on `<html>`), the shadcn default. Add `@custom-variant dark (&:is(.dark *));` once in the CSS (shadcn v4 init writes it).

---

## 2. Core mapping (emitted by theme-css.js)

Hex is the authored value; the emitted CSS is the OKLCH equivalent. Ratios are WCAG 2.x, recomputed in the Step 4.7 gate.

| CSS var | Tailwind utility | Light | Dark | Used by | Pair ratio (L / D) |
|---|---|---|---|---|---|
| `--background` | `bg-background` | `#FAF4EA` cream | `#1E1611` | page, chat canvas | fg 12.50 / 14.82 |
| `--foreground` | `text-foreground` | `#3B2A1E` walnut | `#F3E9D8` | all text | — |
| `--card` | `bg-card` | `#E9D8B8` spruce | `#2E221A` | agent bubbles, login card | 9.75 / 12.84 |
| `--card-foreground` | `text-card-foreground` | `#3B2A1E` | `#F3E9D8` | text in bubbles/cards | — |
| `--popover` | `bg-popover` | `#FFFCF6` paper | `#2E221A` | inputs, Select content, sheets, product card | 13.35 / 12.84 |
| `--popover-foreground` | `text-popover-foreground` | `#3B2A1E` | `#F3E9D8` | menu items | — |
| `--primary` | `bg-primary` | `#A54A29` terracotta | `#D9734C` | action only: CTA, send, retry | label 5.31 / 5.52 |
| `--primary-foreground` | `text-primary-foreground` | `#FAF4EA` | `#1E1611` | button labels, send icon | — |
| `--secondary` | `bg-secondary` | `#E9D8B8` | `#2E221A` | secondary button, chips | 9.75 / 12.84 |
| `--accent` | `bg-accent` | `#C98A2B` honey | `#E0A94F` | Radix highlighted item, selected marks | walnut 4.66 / night 8.45 |
| `--accent-foreground` | `text-accent-foreground` | `#3B2A1E` | `#1E1611` | text on honey (never cream) | — |
| `--muted` | `bg-muted` | `#E9D8B8` | `#2E221A` | quiet fills, disabled fill | — |
| `--muted-foreground` | `text-muted-foreground` | `#6B5444` | `#C9B8A0` | timestamps, sublines, handoff label | 6.45 cream, 5.03 spruce, 6.89 paper / 9.21, 7.98 |
| `--destructive` | `bg-destructive` / `text-destructive` | `#9A2E24` oxblood | `#FC8777` | errors, always with `CircleAlert` + words | 6.88 / 7.53 |
| `--border` | `border-border` | `#D8C29C` grain line | `#564337` | decorative hairlines only (not a boundary) | n/a |
| `--input` | `border-input` | `#6B5444` | `#8A7668` | every form control boundary (Input, Select trigger, composer) | 6.45 / 4.14 (non-text 3:1) |
| `--ring` | `outline-ring` / `ring-ring` | `#3B2A1E` | `#F3E9D8` | focus ring, 2px + 2px offset | 12.50 / 14.82 |
| `--radius` | `rounded-lg` (= 12px) | `12px` | — | cards; `rounded-md` 8px inputs, `rounded-sm` 6px chips | — |
| `--success` | `text-success` | `#46602B` moss | `#9ABA7E` | honest badge, done stage | 6.47 / 8.23 |
| `--warning` | `text-warning` | `#8A5A14` honey deep | `#E0A94F` | promo % (paper/cream only in light) | 5.40 / 8.45 |
| `--info` | `text-info` | `#6B5444` | `#C9B8A0` | calm notices, never blue | 6.45 / 9.21 |
| `--font-sans` | `font-sans` | Source Sans 3 stack | — | everything in chat | — |
| `--font-display` | `font-display` | Fraunces stack | — | headlines only, never in chat | — |
| `--font-mono` | `font-mono` | system mono | — | none in UI | — |
| `--sidebar*`, `--chart-*` | shadcn defaults | see `.yml` | see `.yml` | unused in the POC; mapped for completeness | — |

shadcn's radius scale derives from `--radius`: `--radius-sm = calc(var(--radius) - 4px)` = 8px, `--radius-md = calc(var(--radius) - 2px)` = 10px. The brand wants 6 / 8 / 12, so override them in `@theme inline` (Section 5) instead of using shadcn's calc defaults.

---

## 3. What tokens cannot express (why Sections 4–5 exist)

| Need | Why not a shadcn token | Solution |
|---|---|---|
| User bubble walnut fill + cream text | shadcn has no "inverse surface" | `--user-bubble`, `--user-bubble-foreground` |
| Primary hover/pressed `#93401F` | shadcn uses `hover:bg-primary/90` (opacity), which lightens terracotta on cream and drifts contrast | `--primary-hover` (cream label 6.41 / night label 6.97) |
| Decorative honey (avatar disc, typing dots, rail rule) distinct from `--accent` | `--accent` is a Radix highlight surface; decorative honey must not be tied to menu behavior | `--brand` |
| Honey as text | `--accent` honey fails as text on light (2.68) | `--brand-text` `#8A5A14` (light only; dark uses `--warning`) |
| Paper as a named surface independent of popovers | `--popover` is paper in light but walnut in dark; inputs need "paper" semantics explicitly | `--paper` |
| Chat header wood rail + honey rule | no header token in shadcn | `--rail`, `--rail-foreground`, `--rail-muted`, `--rail-rule` |

---

## 4. Brand extensions (hand-written, paste after the generated block)

```css
/* Empório brand extensions — NOT emitted by theme-css.js. Values trace to
   emporio-da-musica.yml header comments + STYLE.md "Brand extensions". */
:root {
  --user-bubble: #3B2A1E;              /* walnut */
  --user-bubble-foreground: #FAF4EA;   /* cream, 12.50 */
  --primary-hover: #93401F;            /* terracotta deep, cream label 6.41 */
  --brand: #C98A2B;                    /* honey, decorative only */
  --brand-text: #8A5A14;               /* honey as text: cream 5.40 / paper 5.77; never on spruce (4.22) */
  --paper: #FFFCF6;
  --rail: #3B2A1E;                     /* wood rail fill */
  --rail-foreground: #FAF4EA;          /* 12.50; also the focus ring color inside the rail */
  --rail-muted: #E9D8B8;               /* subline 9.75 */
  --rail-rule: #C98A2B;                /* 3px honey bottom rule, 4.66 vs rail (non-text) */
}
.dark {
  --user-bubble: #5A4130;
  --user-bubble-foreground: #F3E9D8;   /* 7.82 */
  --primary-hover: #E58B66;            /* night label 6.97 */
  --brand: #E0A94F;
  --brand-text: #E0A94F;               /* = --warning dark: 8.45 base / 7.32 surface */
  --paper: #2E221A;                    /* = --popover dark; paper-white would glare at night */
  --rail: #5A4130;
  --rail-foreground: #F3E9D8;          /* 7.82 */
  --rail-muted: #C9B8A0;               /* 4.86 */
  --rail-rule: #E0A94F;                /* 4.46 vs rail */
}
```

Note: STYLE.md leaves `--brand-text` and `--paper` undefined in `.dark`. The values above close that gap with existing dark tokens (`--warning`, `--popover`), both already validated in the Step 4.7 gate.

---

## 5. `@theme inline` bridge

```css
@theme inline {
  /* shadcn init writes the --color-* lines for core vars; keep them. Add: */
  --color-user-bubble: var(--user-bubble);
  --color-user-bubble-foreground: var(--user-bubble-foreground);
  --color-primary-hover: var(--primary-hover);
  --color-brand: var(--brand);
  --color-brand-text: var(--brand-text);
  --color-paper: var(--paper);
  --color-rail: var(--rail);
  --color-rail-foreground: var(--rail-foreground);
  --color-rail-muted: var(--rail-muted);
  --color-rail-rule: var(--rail-rule);
  --color-success: var(--success);
  --color-warning: var(--warning);
  --color-info: var(--info);

  /* Brand radius scale: 6 / 8 / 12 (replaces shadcn's calc() defaults) */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: var(--radius);   /* 12px */

  /* Walnut-tinted elevation (.yml tokens.elevation) */
  --shadow-sm: 0 1px 2px rgb(59 42 30 / 0.06);
  --shadow-md: 0 2px 6px rgb(59 42 30 / 0.08);
  --shadow-lg: 0 8px 20px rgb(59 42 30 / 0.10);
  --shadow-xl: 0 16px 32px rgb(59 42 30 / 0.12);

  /* Motion */
  --ease-brand: cubic-bezier(0.33, 1, 0.68, 1);
  --animate-arrive: arrive 150ms var(--ease-brand);
  --animate-breathe: breathe 4s ease-in-out infinite;
}
```

Keyframes (`arrive`, `breathe`, `dot`), grain surfaces and `.tnum` / `.font-display` treatments are in [STYLE.md → Implementation](../STYLE.md#implementation); copy them verbatim into the same file.

Resulting utilities: `bg-user-bubble`, `text-user-bubble-foreground`, `hover:bg-primary-hover`, `bg-brand`, `text-brand-text`, `bg-paper`, `bg-rail`, `text-rail-foreground`, `text-rail-muted`, `border-rail-rule`, `outline-rail-foreground`, `text-success`, `text-warning`, `text-info`, `animate-arrive`, `animate-breathe`.

---

## 6. Base layer

```css
@layer base {
  * { @apply border-border outline-ring/50; }      /* shadcn default; ring opacity is replaced per component */
  html { font-size: 100%; }                         /* never shrink below 16px */
  body { @apply bg-background text-foreground font-sans antialiased; line-height: 1.5; }
  :focus-visible { outline: 2px solid var(--ring); outline-offset: 2px; }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; }
  }
}
```

Replace shadcn's default `focus-visible:ring-[3px] focus-visible:ring-ring/50` on every generated primitive with the brand focus recipe (`outline-2 outline-ring outline-offset-2`). A 50%-opacity ring is not part of this brand: walnut at full strength is what passes 3:1.

---

## 7. Component inventory

| Component | Tier | Source | Spec |
|---|---|---|---|
| Button | 2 — override | shadcn `button` | [button.md](./button.md) |
| Input / composer | 2 — override | shadcn `input`, `textarea`, `label` | [input.md](./input.md) |
| Select | 2 — override | shadcn `select` (Radix) | [select.md](./select.md) |
| Card, Badge, Separator, Sheet, Avatar | 1 — tokens only | shadcn | this file (no extra spec) |
| ChatBubble (+ transcript) | 3 — custom | — | [chat-bubble.md](./chat-bubble.md) |
| TypingIndicator | 3 — custom | — | [typing-indicator.md](./typing-indicator.md) |
| HandoffBubble | 3 — custom | composes ChatBubble | [handoff-bubble.md](./handoff-bubble.md) |
| ProductCard | 3 — custom | — | [product-card.md](./product-card.md) |
| WoodRailHeader | 3 — custom | — | [wood-rail-header.md](./wood-rail-header.md) |
| WarmupStatus | 3 — custom | — | [warmup-status.md](./warmup-status.md) |
| CustomerSelector | 3 — custom | composes Select | [customer-selector.md](./customer-selector.md) |

Tier-1 notes: Card uses `bg-card rounded-lg p-6 md:p-8`, no border on cream, no shadow. Badge `secondary` variant only (spruce + walnut); never the `default` (terracotta) variant, because badges are not clickable. Sheet/Dialog use `bg-popover shadow-lg`. Avatar holds the honey disc asset.
