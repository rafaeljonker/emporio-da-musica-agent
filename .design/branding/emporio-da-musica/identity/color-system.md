# Color System

> Phase: identity | Brand: emporio-da-musica | Generated: 2026-11-05

---

User-confirmed direction: **"Tampo de spruce (claro)"**. A light, warm interface that feels like "balcão de loja de bairro numa manhã de sábado": daylight on a pale spruce top, honey varnish, walnut counter, one terracotta price-tag accent.

Enriched 2026-11-05 by `/gsp-color --enrich`: contrast ratios computed with the WCAG 2.x relative-luminance formula, OKLCH scales and role tokens in [`palettes.json`](./palettes.json). Hex values below are the creative picks except where marked **adjusted**.

## Composition Strategy

**60-30-10 with single-accent discipline for actions.**

| Share | Role | Color |
|-------|------|-------|
| ~60% | Base: page, chat background | Cream |
| ~30% | Content layer: surfaces, agent bubbles, text | Spruce + Walnut |
| ~10% | Brand presence: avatar, logo icon, header details, focus/active marks | Honey |
| <5% | Action only: primary button, send button | Terracotta |

Terracotta is the "Neutral + single accent" layer: it appears **only** where the user can act. If terracotta is on screen and not clickable, it is a bug.

## Core Palette

| Role | Name | Hex | Usage | Rationale |
|------|------|-----|-------|-----------|
| Base | Cream (creme) | `#FAF4EA` | Page background, input fields, login/warm-up canvas | Morning light on paper; warm white that avoids the cold SaaS white |
| Surface | Spruce (tampo) | `#E9D8B8` | Agent bubbles, cards, selector chips (the chat header became the walnut wood rail; see patterns/STYLE.md) | The pale spruce top of an acoustic guitar: the confirmed direction's namesake |
| Primary brand | Honey (mel) | `#C98A2B` | Logo icon disc, assistant avatar, active/selected markers, decorative rules, typing indicator dots | Varnished guitar wood; Everyperson warmth with Sage calm. The brand's "signature" color |
| Text | Walnut (nogueira) | `#3B2A1E` | All body text, headings, icons; user message bubbles (fill) | Dark wood instead of black: warm, high contrast, never harsh |
| Action | Terracotta | `#A54A29` | Primary CTA fill ("Entrar", send), CTA text links | Clay-red price-tag accent; warm urgency-free emphasis, distinct from honey |

## Supporting Neutrals (creative picks, to be tuned in enrichment)

| Role | Hex | Usage |
|------|-----|-------|
| Paper (lightest) | `#FFFCF6` | Raised elements on cream (input inside cards, modal sheet) |
| Grain line / border | `#D8C29C` | Hairline borders, dividers, bubble outlines when needed |
| Walnut muted | `#6B5444` | Secondary text: timestamps, helper text, stage labels |
| Honey deep | `#8A5A14` | Honey used as text or thin icon (links on cream, "selecionado" labels) |
| Terracotta deep | `#93401F` | Hover/pressed CTA, and fallback CTA fill if enrichment finds `#B5532F` too weak |

## Semantic Colors

No cold blues or greys, so semantics stay in the wood/earth family and are **always paired with an icon and words** (never color alone).

| Meaning | Hex | Note |
|---------|-----|------|
| Success | `#46602B` (moss / mata) **adjusted** from `#4F6B32` | "Pedido confirmado", "Pronto" stage complete. Old value gave 4.30:1 on spruce (fail); new gives 5.05:1 |
| Warning | `#8A5A14` (honey deep) | Shares the honey family; text label carries the meaning |
| Error | `#9A2E24` (oxblood / vinho) | Must read as clearly different from terracotta CTA: darker, cooler red, always with an alert icon |
| Info / neutral notice | `#6B5444` (walnut muted) on spruce | No blue "info" state; info is just calm text on a surface |

## Contrast Audit (WCAG 2.2, light mode)

AA: 4.5:1 normal text, 3:1 large text and non-text UI (SC 1.4.11).

| Pair (fg on bg) | Ratio | Result | Use |
|---|---|---|---|
| Walnut on cream | 12.50 | Pass AAA | Body text |
| Walnut on spruce | 9.75 | Pass AAA | Agent bubble text |
| Walnut on paper | 13.35 | Pass AAA | Raised cards, modals |
| Cream on walnut | 12.50 | Pass AAA | User bubble text |
| Cream on terracotta `#A54A29` | 5.31 | Pass AA | Button label, normal text |
| Cream on terracotta deep `#93401F` | 6.41 | Pass AA | Hover/pressed button |
| Walnut muted on cream | 6.45 | Pass AA | Timestamps, helper text |
| Walnut muted on spruce | 5.03 | Pass AA | Timestamps inside agent bubbles |
| Honey deep on cream | 5.40 | Pass AA | Honey-colored text, labels |
| Honey deep on spruce | 4.22 | **Fail** | Do not use; use walnut on spruce |
| Terracotta on cream | 4.52 | Pass AA (thin) | Text links on cream |
| Terracotta on spruce | 3.53 | **Fail** (text) | Use terracotta deep (5.00) for links on spruce |
| Oxblood error on cream | 6.88 | Pass AA | Error text/icon |
| Oxblood error on spruce | 5.37 | Pass AA | Error inside bubbles |
| Moss success `#46602B` on cream | 6.47 | Pass AA | Success text/icon |
| Moss success `#46602B` on spruce | 5.05 | Pass AA | Success inside bubbles |
| Honey on cream | 2.68 | Fail (text); decorative only | Avatar disc, rules, typing dots |
| Walnut glyph on honey | 4.66 | Pass AA, 3:1 non-text | Avatar glyph. Cream glyph on honey is 2.68, forbidden |
| Walnut ring on cream / spruce | 12.50 / 9.75 | Pass (3:1) | Focus ring |
| Walnut ring on terracotta button | 2.76 | Fail if adjacent | Ring must keep a 2 px cream gap (outline-offset) so it never touches the fill |

**Decisions**
- Decision (2026-11-05): the original terracotta `#B5532F` cleared 4.5:1 by only 0.02 (4.52), so the action fill moved to `#A54A29` (5.31:1 with the cream label), which is visually the same terracotta with a safe margin. Hover/pressed stays `#93401F` (6.41). Kept as the CTA fill; the label must be `#FAF4EA` or lighter (never dimmed, no opacity). If the cream or terracotta is ever tweaked, switch the fill to terracotta deep `#93401F`. Hover/pressed already uses it.
- Success token darkened (see Semantic Colors). Warning (honey deep) is text on cream or paper only; on spruce use walnut text with the warning icon.
- Error vs CTA: ratio between oxblood and terracotta deep is 1.07 (near-identical luminance), so distinction rests on hue/darkness plus the mandatory alert icon and words. Color-vision-deficiency simulation not run; icon + text is the guarantee.
- Focus ring: 2 px walnut, 2 px cream offset gap. Against cream 12.50 and spruce 9.75 (3:1 required).

## Chat-specific Mapping

| Element | Fill | Text |
|---------|------|------|
| Chat background | Cream | — |
| Agent bubble | Spruce | Walnut |
| User bubble | Walnut | Cream |
| Typing indicator | Spruce bubble | Honey dots (decorative; accessible label carries meaning) |
| Send button | Terracotta | Cream icon |
| Header | Walnut "wood rail" with a 3px honey rule at the bottom (refine 2026-11-05) | Cream/spruce text; honey avatar disc; cream focus ring |

User bubbles in walnut is a deliberate call: it separates "me" from "the store" instantly on a small screen, and it reads as the darker wood of the counter on the customer's side. Honey is not used for user bubbles because it would put the brand color on the customer's words and it is too light for text.

## Dark Mode Direction

Secondary priority for the POC. Concept: **"a loja depois das 18h"**. Tokens are named by role (see `palettes.json`).

| Role | Light | Dark | Dark contrast |
|------|-------|------|---------------|
| Base | Cream `#FAF4EA` | Walnut night `#1E1611` | text on base 14.82 |
| Surface | Spruce `#E9D8B8` | Dark walnut `#2E221A` | text on surface 12.84 |
| Text | Walnut `#3B2A1E` | Cream `#F3E9D8` | - |
| Brand | Honey `#C98A2B` | Lighter honey `#E0A94F` | 8.45 on base, 7.32 on surface (Pass) |
| Action fill | Terracotta `#A54A29` | `#D9734C` | 5.52 on base, 4.78 on surface (Pass as text/icon) |
| Action label | Cream | **Dark `#1E1611`** | 5.52 (Pass). Cream label on `#D9734C` is 2.68 (Fail) |
| User bubble | Walnut, cream text | `#5A4130`, cream `#F3E9D8` text | 7.82 (Pass) |
| Focus ring | Walnut | Cream `#F3E9D8` | 14.82 base, 12.84 surface |

Notes: honey on the user bubble is 4.46, so honey stays decorative there. Never pure black; never cool grey surfaces.

## Semantic Token Map

| Token | Light | Dark |
|-------|-------|------|
| `--color-bg` | `#FAF4EA` | `#1E1611` |
| `--color-surface` | `#E9D8B8` | `#2E221A` |
| `--color-text` | `#3B2A1E` | `#F3E9D8` |
| `--color-text-muted` | `#6B5444` | `#C9B8A0` (9.21 on base, 7.98 on surface) |
| `--color-brand` | `#C98A2B` | `#E0A94F` |
| `--color-action` | `#A54A29` | `#D9734C` |
| `--color-action-hover` | `#93401F` | `#E58B66` (6.97 on base, 6.04 on surface) |
| `--color-on-action` | `#FAF4EA` | `#1E1611` |
| `--color-error` | `#9A2E24` | pending dark audit |
| `--color-success` | `#46602B` | pending dark audit |
| `--color-warning` | `#8A5A14` | pending dark audit |
| `--color-focus-ring` | `#3B2A1E` | `#F3E9D8` |

OKLCH 11-stop scales (neutral, spruce, honey, terracotta, error, success) are in `palettes.json`. They were generated locally (fixed hue and chroma, stepped lightness, gamut-clamped), not from tints.dev, so stop 500 is not the source hex. Use the named role tokens above, not scale stops, for the audited pairs.

## Anti-patterns

- No blue anywhere (including links and info states).
- No red "sale" banners; terracotta never becomes a promo badge background.
- No gradients across large surfaces; wood/paper texture, if used, is a faint overlay that must not reduce text contrast.
- No black-and-gold luxury pairing.

## Related

- [Logo Directions](./logo-directions.md)
- [Typography](./typography.md)
- [Brand Applications](./brand-applications.md)
