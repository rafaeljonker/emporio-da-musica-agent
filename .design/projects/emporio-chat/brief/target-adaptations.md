# Target Adaptations

> Phase: brief | Project: emporio-chat | Generated: 2026-11-05
> Brand contract: [STYLE.md](../../../branding/emporio-da-musica/patterns/STYLE.md) · Tokens: [emporio-da-musica.yml](../../../branding/emporio-da-musica/patterns/emporio-da-musica.yml)

## Token overrides

None. The project uses the brand tokens as-is (core vars via `emporio-da-musica.theme.json`, brand extensions and `@theme inline` per [token-mapping.md](../../../branding/emporio-da-musica/patterns/components/token-mapping.md)). Every new element below reuses existing tokens; no new color is introduced.

## Component adaptations

### WarmupStatus → project variant ([warmup-status.md](../../../branding/emporio-da-musica/patterns/components/warmup-status.md))

| Brand spec | Project adaptation | Why |
|-----------|-------------------|-----|
| Stage label (generic server wording) | "Ligando a GPU" (`Server` icon kept) | Spec 5 names the stage; the evaluator is technical |
| Explanation: generic "servidor que desliga" | Names the model and the reason: Gemma 4 31B on its own GPU (Modal) that sleeps when idle to avoid cost | Spec 5 asks for the plain-language why |
| "never an estimate of remaining time" | Add a static expected total, rounded up to the next 10 s: "Normalmente leva cerca de {N} s." Elapsed timer still counts up. Never a countdown, never "faltam" | Spec asks for estimated + elapsed time; brand forbids fake progress. A fixed expectation is honest; a countdown would lie when it overruns |
| — | One merged note with the measured number: "Com a máquina já ligada, a primeira mensagem sai em uns 2 s. Se escrever agora, a mensagem vai sozinha quando ele ficar pronto." Value from config/backend, not hardcoded (design revision 1) | Spec 5: show that production would not wait |
| Rendered as its own `<main>` | Rendered as the body of the chat shell; wood rail, demo strip and composer stay | Enables queued message; matches wood-rail "warming" state |
| — | **Queued message**: composer enabled during warm-up. On send, the user bubble appears in the log with a 14px `text-muted-foreground` line "Vai assim que o assistente ficar pronto" (`Clock` 16px). Sent once on `ready`; one queued group (later sends add bubbles to it, flushed joined by `\n`); "Desfazer" returns the text to the composer; kept in `sessionStorage` (design revision 1) | Spec 5: "if the person already typed, the message is queued and sent on its own" |
| — | **`mode: local_cpu`**: headline unchanged; explanation "O modelo está rodando na sua máquina, sem GPU. Cada resposta pode levar de 30 s a alguns minutos." Stages: "Carregando o modelo" → "Pronto pra conversar" (no GPU stage). After ready, a persistent quiet notice under the demo strip repeats the slow-reply warning | Spec 7.14 warning #3 |
| — | **`mode: provider_api`**: no warm-up body; chat is ready on arrival | Spec 7.14 fast path |
| Retry | "Tentar de novo" only on `failed`; re-issues `POST /warm`; elapsed continues from the backend `started_at` (never 0 s). No retry in the long wait (design revision 1) | A long wait is not a failure; restarting a loading container loses progress |

Stage source contract (for backend): `POST /auth/login` and `GET /warm/status → { mode, stage: "server_starting" | "model_loading" | "ready" | "failed", started_at, expected_seconds }`. `started_at` = first `POST /warm` of this cold start; `expected_seconds` = measured p75 of recent cold starts per mode (never the target). The UI never advances a stage on a timer (design revision 1).

### ChatTranscript / ChatBubble ([chat-bubble.md](../../../branding/emporio-da-musica/patterns/components/chat-bubble.md))
- SSE mapping: `typing` → show TypingIndicator; `bubble {kind: "text" | "handoff" | "product", delay_ms}` → append complete bubble (pacing from the backend: bubble 1 at 0 ms, 2–3 paced, ≤ 3 s per reply); `metrics` → summary, last reply, history; `done` → hide typing; `error` → "Perdi o fio da conversa aqui." (or "Perdi o fio no meio da resposta." after ≥ 1 bubble) + "Manda de novo?".
- Composer disabled for send while a reply streams (text entry stays enabled).

### HandoffBubble, ProductCard
Used as specified. Triggered only by structured flags from the backend (`kind`, `honest_pick`, `promotion`), never inferred on the client.

### CustomerSelector ([customer-selector.md](../../../branding/emporio-da-musica/patterns/components/customer-selector.md))
- First item "Sem identificação" (second line "o assistente vai pedir o número do pedido"), default selection. Divider on switch: "Agora conversando sem identificação" / "Agora conversando como {primeiro nome}".
- Items from `/customers` (name + city only; no phone or e-mail on screen).

### MetricsPanel (new, project-level)
- Demo tool, so it lives in the demo strip, collapsed by default: native `<details>`/`<summary>` "Métricas" (no new dependency).
- Per turn: input/output tokens, latency per stage (guard, LLM, tools, vector search), cost in R$. Session total line.
- Tokens: `bg-popover`, 14px `text-muted-foreground` labels, values `text-foreground tnum`. No terracotta, no chart. Exact layout is a design-phase decision.

### Login
As [brand-applications.md §1](../../../branding/emporio-da-musica/identity/brand-applications.md): spruce card with wood grain, labels above, full-width "Entrar", demo note. Submitting state "Entrando…" (`aria-busy`, no spinner).

## Platform considerations
- Mobile-first: 360 px min; demo strip wraps to two rows below `sm` (tag + selector, then metrics toggle); label sr-only on narrow screens.
- `dvh` for the chat shell height; composer sticky with `env(safe-area-inset-bottom)`; rail uses `env(safe-area-inset-top)`.
- Desktop: chat column `max-w-2xl` centered on cream canvas; rail spans full width.
- Dark mode supported via `.dark` class (brand ships dark tokens); default follows `prefers-color-scheme`.
- Reduced motion: breathing ring, typing dots and arrive fade off. Reduced data: grain off.

## Implementation target mapping (shadcn)

| Design component | Target primitive | Notes |
|-----------------|------------------|-------|
| Primary / secondary / ghost / link / icon buttons | shadcn `button` (cva replaced per button.md) | send = `size="icon"` |
| Login fields | `input` + `label` | |
| Composer | `textarea` (auto-grow) + `button` | rounded-full |
| CustomerSelector | `select` | brand override per select.md |
| Login card | `card` | `.surface-wood` |
| Boca avatar | `avatar` | `alt=""` |
| Honest badge | `badge` (variant restyled) | moss text, never terracotta |
| Transcript, bubbles, typing, handoff, product card, warm-up, wood rail | plain components in `frontend/src/chat/`, `frontend/src/warmup/` | no shadcn equivalent |
| MetricsPanel | native `<details>` | no `collapsible` install |
| Error lines | inline `role="alert"` | no toast |

## Related
- [scope.md](./scope.md) · [install-manifest.md](./install-manifest.md)
