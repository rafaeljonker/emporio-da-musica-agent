# WoodRailHeader — custom spec

> Tier 3 | Brand: emporio-da-musica | Source: `.yml` `patterns.nav`, `effects.surfaces.wood-rail`, constraint "wood rail on every chat screen"

## Anatomy

```
<header> walnut rail, 3px honey bottom rule, sticky top
├─ Avatar 40px honey disc (alt="")
├─ Identity block
│  ├─ <h1> "Assistente da Empório"   16px 600 --rail-foreground
│  └─ subline "assistente virtual da loja"   14px --rail-muted
└─ Actions (right): "Sair" ghost button (and CustomerSelector trigger on wide screens, see customer-selector.md)
```

## Tokens

| Part | Classes | Ratio (L / D) |
|---|---|---|
| container | `sticky top-0 z-10 flex items-center gap-3 px-4 py-3 bg-rail border-b-[3px] border-rail-rule pt-[max(0.75rem,env(safe-area-inset-top))]` | rule vs rail 4.66 / 4.46 (non-text) |
| title | `text-base font-semibold text-rail-foreground` | 12.50 / 7.82 |
| subline | `text-sm text-rail-muted` | 9.75 / 4.86 |
| avatar | honey disc on walnut | 4.66 / 4.46 (non-text) |
| ghost action | `text-rail-foreground hover:bg-rail-foreground/10` | 12.50 / 7.82 |
| focus inside rail | `[&_:focus-visible]:outline-rail-foreground` (cream ring; walnut would vanish) | 12.50 / 7.82 |

Solid colors only: no grain, no image, no gradient, no motion. It stays under `prefers-reduced-data` and in dark mode.

## States

| State | Treatment |
|---|---|
| default | as above |
| agent offline / warming | header unchanged; the chat body shows [WarmupStatus](./warmup-status.md) |
| scrolled | no shadow change, no shrink (no layout animation) |

## A11y

- `<header>` landmark; the title is the page `<h1>` on the chat screen.
- The subline makes clear it is a virtual assistant (not a person) in visible text.
- Avatar `alt=""` because the name is adjacent text.
- Icon-only actions: `aria-label="Sair"`. Targets ≥ 44px.

## Copy (pt-BR)

"Assistente da Empório" · "assistente virtual da loja" · "Sair". "Empório" always with the accent.
