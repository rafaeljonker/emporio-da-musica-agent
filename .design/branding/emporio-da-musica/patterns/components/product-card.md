# ProductCard — custom spec

> Tier 3 | Brand: emporio-da-musica | Source: `.yml` `patterns.product-card` (refine 2026-11-05)

Note: identity/brand-applications.md §3 said "no price cards"; the confirmed `.yml` refine added this card. The `.yml` wins.

## Anatomy

```
<article> paper card inside the agent group (avatar column spacer on the left)
├─ Name                 16px 600 walnut
├─ HonestBadge?         CircleCheck + "Na medida pro seu nível" (only when flagged)
├─ PriceLine            final price 20px 600 tabular   | or PromoLine (3 parts)
└─ PixLine?             14px muted, e.g. "R$ 569,91 no PIX (5% off)"  (never together with a promo)
```

## Tokens

| Part | Classes | Ratio (L / D) |
|---|---|---|
| container | `max-w-[80%] rounded-lg border border-border bg-popover p-4 shadow-sm` | — |
| name | `text-base font-semibold text-foreground` | 13.35 / 12.84 |
| honest badge | `inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-0.5 text-sm font-semibold text-success` + `CircleCheck` 16px | 6.91 / 7.13 |
| price | `text-xl font-semibold text-foreground tnum` | 13.35 / 12.84 |
| PIX line | `text-sm text-muted-foreground tnum` | 6.89 / 7.98 |
| promo original | `text-muted-foreground line-through` | 6.89 / 7.98 |
| promo percent | `font-semibold text-warning` | 5.77 / 7.32 |
| promo final | `font-semibold text-foreground` | 13.35 / 12.84 |

Never: terracotta (the card is not clickable), red sale banner, `text-warning` on spruce (4.22), a discount without the original price, PIX discount stacked on a promo.

## Promo rule

Always three parts on one line: "De R$ 2.399" · "18% off" · "R$ 1.967,18". The word "De" carries the meaning; the strike is decorative. Only active promotions (`is_active = 1`) render; otherwise the plain price line.

## Data / formatting

- Format with `Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" })`; drop ",00" for whole values to match voice ("R$ 849").
- Honest badge renders only from a backend flag (the agent recommended the cheaper fit), never computed by the UI.

## States

| State | Treatment |
|---|---|
| default | name + price |
| honest pick | + honest badge above the price |
| promo | promo line replaces price line; no PIX line |
| out of stock | 14px `text-muted-foreground` line "Sem estoque no momento" + `CircleSlash` 16px; price still shown; no strike, no red |

## A11y

- `<article aria-labelledby={nameId}>`; name is an `<h3>`-level text inside the log (or `<p>` with `id` if heading levels would conflict, decide in build).
- Promo line has an sr-only rewrite so the strike is not needed: `<span className="sr-only">Preço original R$ 2.399, 18% de desconto, sai por R$ 1.967,18</span>` and the visual line `aria-hidden`.
- Not focusable (no actions in the POC). If a future action is added, it is a separate Button, not a clickable card.

## Copy examples (pt-BR)

Agent bubble before the card: "Pro seu nível, o C40 de R$ 599,90 dá conta tranquilo." Card: "Yamaha C40 Nylon Natural" · "Na medida pro seu nível" · "R$ 599,90" · "R$ 569,91 no PIX (5% off)".
