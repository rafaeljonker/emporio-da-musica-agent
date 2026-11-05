# Button — override spec (shadcn `button`)

> Tier 2 | Brand: emporio-da-musica | Source: [../emporio-da-musica.yml](../emporio-da-musica.yml) `patterns.button-*`, `effects`

## Why override

Tokens alone leave three brand rules broken:
1. shadcn hover is `hover:bg-primary/90` (opacity). The brand hover is a solid darker terracotta `--primary-hover` (#93401F, cream label 6.41).
2. shadcn focus is `ring-[3px] ring-ring/50`. The brand focus is a 2px walnut outline with 2px offset; on terracotta the walnut must never touch the fill (2.35:1 light, 2.68:1 dark), so a 2px background-colored gap is drawn with `box-shadow`.
3. shadcn `destructive` uses `text-white`; dark-mode oxblood (#FC8777) needs the night label (`text-primary-foreground`, 7.53).

## Variants

| Variant | Classes (replace the shadcn cva entries) | Use |
|---|---|---|
| `default` (primary) | `bg-primary text-primary-foreground hover:bg-primary-hover active:bg-primary-hover active:scale-[0.98]` | the single action per view: "Entrar", send, "Tentar de novo" |
| `secondary` | `border border-input bg-secondary text-foreground hover:bg-card` (on spruce: `bg-transparent hover:bg-secondary`) | "Sair", "Cancelar" |
| `ghost` | `bg-transparent text-foreground hover:bg-muted` | icon buttons inside rows |
| `link` | `text-foreground underline underline-offset-3 decoration-1 hover:decoration-2` | inline retry: "Manda de novo?" |
| `destructive` | `bg-destructive text-primary-foreground hover:bg-destructive/90` + `CircleAlert` icon | not used in the POC; kept for completeness |
| `outline` | alias of `secondary` | — |

Base (all variants): `inline-flex items-center justify-center gap-2 rounded-full font-sans font-semibold text-base transition-[color,background-color,transform] duration-150 ease-brand disabled:pointer-events-none`.

## Sizes

| Size | Classes | Note |
|---|---|---|
| `default` | `h-11 px-6` | 44px target (WCAG 2.5.8 needs 24; brand uses 44 on mobile) |
| `sm` | `h-9 px-4` | only for non-primary actions in dense rows |
| `icon` | `size-11` | send button: 44px circle, `Send` 20px |

No `lg`; full-width CTA uses `w-full` on `default`.

## States

| State | Primary | Secondary |
|---|---|---|
| rest | terracotta, cream label (5.31) | spruce fill, walnut label, 1px `--input` border |
| hover | `--primary-hover` (6.41) | spruce/card fill |
| pressed | `--primary-hover` + `scale-[0.98]`, 100ms | same |
| focus-visible | `outline-2 outline-ring outline-offset-2 shadow-[0_0_0_2px_var(--background)]` | `outline-2 outline-ring outline-offset-2` |
| disabled | `bg-muted text-muted-foreground` (5.03), no opacity | `bg-muted text-muted-foreground border-input` |
| loading | label stays; `aria-busy="true"`; no spinner (brand constraint). Example: "Entrando…" | — |

Disabled uses explicit muted tokens instead of `opacity-50` so the label stays legible (5.03) even though WCAG exempts disabled controls.

Inside the wood rail the focus outline switches to cream: `outline-rail-foreground` (12.50) and the gap uses `var(--rail)`.

## Code hint

```tsx
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-full font-semibold text-base transition-[color,background-color,transform] duration-150 ease-brand focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2 disabled:pointer-events-none disabled:bg-muted disabled:text-muted-foreground",
  { variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary-hover active:bg-primary-hover active:scale-[0.98] focus-visible:shadow-[0_0_0_2px_var(--background)]",
        secondary: "border border-input bg-secondary text-foreground hover:bg-card",
        ghost: "hover:bg-muted text-foreground",
        link: "text-foreground underline underline-offset-3 hover:decoration-2 h-auto px-0",
        destructive: "bg-destructive text-primary-foreground hover:bg-destructive/90",
      },
      size: { default: "h-11 px-6", sm: "h-9 px-4", icon: "size-11" },
    }, defaultVariants: { variant: "default", size: "default" } })

<Button size="icon" aria-label="Enviar mensagem">
  <Send size={20} strokeWidth={1.75} absoluteStrokeWidth aria-hidden />
</Button>
```

## Rules

- One `default` (terracotta) button per view. Terracotta on anything not clickable is a bug.
- Sentence case, Source Sans 3 600, 16px. Never Fraunces, never ALL CAPS.
- Icon-only buttons always carry a pt-BR `aria-label`: "Enviar mensagem", "Trocar cliente", "Sair".
- Copy: "Entrar", "Tentar de novo", "Enviar mensagem", "Sair".
