# WarmupStatus — custom spec

> Tier 3 | Brand: emporio-da-musica | Source: Bold Bet 3 "Honest warm-up", identity/brand-applications.md §2, `.yml` constraint "no spinners, progress bars or fake percentages"

Shown while the GPU server cold-starts. Honesty is the brand: the wait is explained, not disguised.

## Anatomy

```
<main> cream canvas (surface-paper, rosette tile 4%), max-w-md centered
├─ Boca icon (breathing, the only motion)        aria-hidden
├─ <h1> "Afinando o atendimento"                 Fraunces 600, display size
├─ explanation paragraph                         Source Sans 3 16px
├─ <div role="status"> stage list                <ol>, 3 items
│   ├─ done      CircleCheck 20px text-success  + label
│   ├─ current   stage icon (Server / Cpu) 20px text-foreground + 4px honey left marker + label 600 + sr-only "em andamento"
│   └─ pending   Circle 20px text-muted-foreground + label muted
├─ elapsed timer  "Esperando há 42 s"            tnum, text-muted-foreground, NOT live
└─ (long wait / failure) explanation + primary "Tentar de novo"
```

Tuning-peg line drawing: one per screen, decorative, `aria-hidden`.

## Real data contract

| Prop | Source | Rule |
|---|---|---|
| `stage` | backend health/readiness endpoint: `"server_starting" \| "model_loading" \| "ready" \| "failed"` | the UI only renders what the backend reports; it never advances a stage on a client timer |
| `startedAt` | timestamp captured when the warm-up began (client clock at first poll) | elapsed = `now - startedAt`, ticks every 1s, counts up, never down, never an estimate of remaining time |
| `expectedSeconds` | config value N for the explanation copy | only used in the sentence "cerca de {N} segundos" |

No progress bar, no percentage, no spinner, no rotating logo.

## Stages (pt-BR labels)

| Stage key | Label |
|---|---|
| `server_starting` | "Ligando a GPU" (`Server` while current) |
| `model_loading` | "Carregando o modelo" (`Cpu` while current) |
| `ready` | "Pronto pra conversar" |

Icon by state: done `CircleCheck` (moss), current the stage icon (walnut), pending `Circle` (muted). All 20px, `strokeWidth={1.75} absoluteStrokeWidth`, `aria-hidden`.

## Tokens

| Part | Token | Ratio (L / D) |
|---|---|---|
| canvas | `bg-background` + `.surface-paper` | — |
| headline | `font-display text-foreground` | 12.50 / 14.82 |
| explanation, current label | `text-foreground` | 12.50 / 14.82 |
| done icon | `text-success` | 6.47 / 8.23 |
| pending label/icon, timer | `text-muted-foreground` | 6.45 / 9.21 |
| current marker | `bg-brand` 4px bar | supplementary (state also in weight + sr-only text) |
| retry | primary Button | 5.31 / 5.52 |

## States

| State | Treatment |
|---|---|
| warming | stages + timer; Boca breathes (`animate-breathe`, off under reduced motion) |
| ready | all three done; route to chat (focus moves to the composer) |
| long wait (elapsed > 2 × N) | add line "Tá demorando mais que o normal. Pode esperar mais um pouco ou tentar de novo." + "Tentar de novo" |
| failed | stop timer; `role="alert"` text "Não consegui ligar o assistente agora. Tenta de novo daqui a pouco." + "Tentar de novo" (focus moves to the button) |

## A11y

- The stage list wrapper is `role="status"` (polite). It is mounted from the start; on each stage change, update a sr-only sentence inside it, e.g. "Carregando o modelo." Announcements happen only on stage changes.
- The timer sits outside any live region (`aria-live="off"`), so it is never announced every second. Wrap the number in `<span className="tnum">`.
- `<ol>` keeps stage order; each item has visible text (state is not icon/color only: done = icon + text, current = semibold + sr-only "em andamento", pending = muted + sr-only "a seguir").
- Failure uses `role="alert"` (this one is an error the user can act on).

## Copy (pt-BR)

- Headline: "Afinando o atendimento"
- Explanation: "O assistente roda num servidor que desliga quando ninguém está usando, e ligar de novo leva cerca de {N} segundos. Já já ele tá pronto."
- Timer: "Esperando há {s} s" (switch to "Esperando há {m} min {s} s" after 60s)
- Retry: "Tentar de novo"
