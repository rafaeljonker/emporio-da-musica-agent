# Screen 01: Chat

> Phase: design | Project: emporio-chat | Generated: 2026-11-05 | Revised: 2026-11-05 (revision 1)
> Brand: [STYLE.md](../../../branding/emporio-da-musica/patterns/STYLE.md) · Mockup: [mockups/chat.html](./mockups/chat.html) (`?autoplay`)
> Revision 1: metrics settled on the collapsed "Métricas" `<details>` (session totals in the summary, per-turn history inside); 16px summary and link button; selector keeps the thread (SC 3.2.2); send keeps focus; partial-reply error; handoff label states the action; demo strip explained once; strip/rail content aligned to the transcript column; typing dots 3:1; short-viewport reflow.

## Purpose

The demo itself. The evaluator talks to the store's agent and judges voice, tool accuracy and cost per turn. It must read like a human store on WhatsApp: plain text bubbles on a wooden counter, with demo tools (customer selector, metrics) visibly separated from store content.

## User flow position

`Login → (warm-up body state, screen 02) → Chat`. The chat shell (rail + demo strip + composer) is mounted from the moment login succeeds; screen 02 is only a body state of this shell. With `mode = provider_api`, the body is the chat from the first frame.

## Layout (mobile-first, 360 px)

```
┌──────────────────────────────────────┐
│ [Boca 40] Assistente da Empório  Sair│  WoodRailHeader: walnut rail, 3px honey rule, sticky top
│           assistente virtual da loja │
├──────────────────────────────────────┤
│ ⚗ Demonstração  Conversar como…      │  <aside aria-label="Demonstração">
│ [Sem identificação               ▾]  │  select wraps to row 2 below sm
│ ◔ Métricas · 3 respostas · R$ 0,0118 │  <details> summary, 16px 600, session totals
├──────────────────────────────────────┤
│ 💻 Modo local, sem GPU: cada resposta│  Local notice (only mode=local_cpu, after warm-up)
├──────────────────────────────────────┤
│                         [user bubble]│  role="log", max-w-2xl centered, overflow-y auto
│                                14:31 │
│ ( ) [agent bubble 1]                 │  1–3 bubbles per reply; bubble 1 at once, 2–3 paced
│     [ProductCard: paper]             │
│ (B) [agent bubble 3]                 │  Boca avatar on the LAST bubble of the group
│     14:31                            │
│ ───── Agora conversando como Ana ─── │  divider after a selector change (thread kept)
│ ( ) [··· typing]                     │  role="status", sibling after the log
├──────────────────────────────────────┤
│ [ Escreve sua mensagem      ] (➤)    │  <form aria-label="Enviar mensagem">, safe-area padding
└──────────────────────────────────────┘
```

- Shell: `flex h-dvh flex-col`; transcript is the only scroll container (`flex-1 min-h-48 overflow-y-auto`, the `12rem` floor keeps it reachable).
- Short viewports (`max-height: 480px`, e.g. 400% zoom at 320 × 256 CSS px): shell switches to `h-auto min-h-dvh`, rail becomes `static`, the page scrolls instead of squeezing the transcript to 0 (SC 1.4.10).
- Column: rail and strip **backgrounds** span the full width; their **content** sits in the same `mx-auto w-full max-w-2xl px-4` column as the transcript, typing and composer, so the selector and Métricas line up with the conversation at 1280 px.
- Spacing: 8px inside a group, 16px on speaker change (chat-bubble.md). Density dial 4: compact like WhatsApp.

## Components

| Component | Spec | Notes |
|---|---|---|
| WoodRailHeader | [wood-rail-header.md](../../../branding/emporio-da-musica/patterns/components/wood-rail-header.md) | `<h1>` "Assistente da Empório"; "Sair" ghost with `LogOut` icon + visible text (clears the demo session) |
| DemoStrip + CustomerSelector | [customer-selector.md](../../../branding/emporio-da-musica/patterns/components/customer-selector.md) | `<aside aria-label="Demonstração">`; first item "Sem identificação" (second line "o assistente vai pedir o número do pedido") |
| MetricsDetails + MetricsPanel | this doc § Metrics | project-level, new |
| LocalModeNotice | this doc § States | `Laptop` 16px + 14px muted text, `border-b border-border` |
| ChatTranscript, MessageGroup, ChatBubble | [chat-bubble.md](../../../branding/emporio-da-musica/patterns/components/chat-bubble.md) | plain text, `whitespace-pre-line`, `overflow-wrap: anywhere` |
| TypingIndicator | [typing-indicator.md](../../../branding/emporio-da-musica/patterns/components/typing-indicator.md) | mounted for the whole session; dots `--muted-foreground` in light (5.03:1 on spruce), honey `#E0A94F` in dark (7.32:1); trough opacity .5 |
| HandoffBubble | [handoff-bubble.md](../../../branding/emporio-da-musica/patterns/components/handoff-bubble.md) | `kind: "handoff"` from SSE; label states what the system did (§ States) |
| ProductCard | [product-card.md](../../../branding/emporio-da-musica/patterns/components/product-card.md) | `kind: "product"`, honest badge only from `honest_pick`; name is `<p id>` + `aria-labelledby` (no `<h3>`: the chat state has no `<h2>`) |
| Composer | [input.md § Chat composer](../../../branding/emporio-da-musica/patterns/components/input.md) | `rounded-full` textarea + 44px terracotta send |

## SSE event → UI

| Event | UI |
|---|---|
| `typing` | TypingIndicator on; sr text set once per reply |
| `bubble {kind: text \| handoff \| product, delay_ms}` | append one complete bubble with `fade-arrive`; typing stays on between bubbles. Bubble 1 has `delay_ms = 0` |
| `metrics {tokens, latency, cost, action}` | stored on the turn; feeds the summary totals, "Última resposta" and one history line. `action` is the backend's word for what happened ("busca no catálogo", "consulta de pedido", "sem ferramenta", "repasse registrado") |
| `done` | typing off; timestamp under the group; send active again |
| `error` before any agent bubble | inline under the user bubble: "Perdi o fio da conversa aqui." + link button "Manda de novo?" |
| `error` after ≥ 1 agent bubble | typing off; bubbles already shown stay; line under the agent group: "Perdi o fio no meio da resposta." + "Manda de novo?" (resends the user's last message once) |

Pacing (resolved): backend-driven, bubble 1 at 0 ms (typing already covered generation), bubbles 2–3 length-proportional, at most 3 s of pacing per reply. Details in [shared/micro-interactions.md](./shared/micro-interactions.md).

## Metrics (decided 2026-11-05: collapsed `<details>` in the demo strip)

- `<details class="metrics"><summary>`: `Gauge` 16px + "Métricas" + session totals " · 3 respostas · R$ 0,0118" (16px 600, values `tnum`), 44px tall, at the end of the strip. Empty session: just "Métricas".
- Panel: `bg-popover`, 1px `border` hairline, `shadow-sm`, 14px body; labels `text-muted-foreground`, values `text-foreground tnum`. No terracotta, no honey, no chart. Block headings are `<p><strong>` (no heading level, A-10).
  1. **Última resposta**: "Tokens: 1.284 de entrada · 96 de saída"; "Tempo: 2,4 s no modelo · 4,1 s na tela" + muted breakdown "filtro 0,12 · geração 2,0 · ferramentas 0,21 · busca 0,08"; "Custo: R$ 0,0042" + muted basis "Estimado: segundos de GPU × preço do Modal" (in `local_cpu`: "R$ 0 (rodando na sua máquina)"). "no modelo" = server time; "na tela" = send to last bubble on screen, including pacing.
  2. **Sessão**: respostas, tokens, custo total, and "Aquecimento: 31 s" once the warm-up reached `ready` (the measured cold start).
  3. **Histórico**: `<ol>`, newest first, one line per turn: "Resposta 3 · 4,1 s · R$ 0,0042 · busca no catálogo".
- Open: panel takes the full strip width (`flex-basis: 100%`); below `md` it is `max-h-[40dvh] overflow-y-auto` so it never takes over the transcript.
- Not a live region: closed-panel updates are silent; the summary text updates in place.

## States

| State | Treatment |
|---|---|
| Empty | rosette line drawing (96 px, `aria-hidden`) + muted "Pergunta de preço, estoque, entrega ou qual instrumento combina com você. Pode mandar." + 14px muted "Na faixa de demonstração, \"Conversar como…\" simula quem manda mensagem pelo WhatsApp." centered |
| Loading (reply in progress) | user bubble rendered immediately (no spinner); TypingIndicator; send `aria-disabled="true"` (stays focusable), textarea enabled |
| Sequential reply | 1–3 bubbles; first at once, the rest paced; avatar moves to the last bubble of the group |
| Product | ProductCard in the agent group; honest badge "Na medida pro seu nível" only when flagged; e.g. Yamaha C70 Nylon Natural, R$ 849, "R$ 806,55 no PIX (5% off)" |
| Handoff | HandoffBubble label from the backend flag: `UserRound` + "Repassado pra equipe", or `Clock` + "Retorno em até 24 horas úteis". Body never promises a callback the demo cannot make: "Isso eu preciso confirmar com a equipe. Já deixei registrado pra eles." History line shows "repasse registrado" |
| Error (no reply) | inline under the failed user bubble, 14px muted text + "Manda de novo?" link button at **16px** (`text-base`, own font size, never `font: inherit`); resends once; never `role="alert"` on bubbles |
| Partial reply error | see SSE table; bubbles kept |
| Customer switched | thread **kept**; divider "Agora conversando como Ana" / "Agora conversando sem identificação" appended to the log (announced as a log addition); a new session id starts below it; no confirm dialog; **focus does not move** (SC 3.2.2) |
| Anonymous | default; order questions make the agent ask for order number + e-mail or phone (agent behavior, no UI change) |
| Local mode | persistent quiet notice under the strip: "Modo local, sem GPU: cada resposta pode levar de 30 s a alguns minutos." |
| Queued message (from warm-up) | see screen 02 § Queued message; on `ready` the queued line and "Desfazer" are replaced by the timestamp and the text is sent once |
| New messages while scrolled up | auto-scroll only when within 80 px of the bottom; otherwise secondary pill "Novas mensagens" above the composer; click scrolls to bottom |

## Interactions

| Trigger | Response |
|---|---|
| Enter in composer | send (Shift+Enter = new line); field clears, focus stays in the textarea |
| Send click / Space / Enter on Send | same; Send uses `aria-disabled` (not `disabled`) while empty or streaming and ignores activation, so focus stays on it |
| Selector change | divider + new session below; previous turns stay; no focus move |
| Summary click | native disclosure |
| "Manda de novo?" | removes the error line, resends the last user message once, focus to the composer |
| Sair | `POST /auth/logout` (or clear session) → login |

Effects used: warm-darken + settle-press (send, Sair), fade-arrive (bubbles), dot-pulse (typing), wood-rail (header). Nothing else moves.

## Accessibility

- Order: rail (h1, Sair) → demo aside (tag, selector, Métricas) → local notice → log → typing status → composer form.
- Landmarks: `header`, `aside aria-label="Demonstração"`, `main`, `form aria-label="Enviar mensagem"`.
- `role="log"` `aria-label="Conversa com o assistente da Empório"` `tabIndex=0`; bubbles appended only when complete; sr-only "Assistente: " / "Você: " prefix on every bubble.
- TypingIndicator `role="status"` outside the log, mounted always, text "O assistente está digitando" set once per reply.
- ProductCard `<article aria-labelledby>` on a `<p id>`; promo line has an sr-only rewrite (product-card.md).
- Focus never jumps into the log. After send, focus stays where the user activated (textarea or Send). Selector change never moves focus. After warm-up `ready`, see screen 02.
- Targets ≥ 44 px (send, Sair, selector, summary); link buttons ≥ 24 px. Focus: walnut 2px + 2px offset; cream ring inside the rail.
- Reduced motion: no fade, no dot pulse (static dots), pacing unchanged (it is content timing, not motion).
- Dark mode via tokens; all pairs from the brand `.yml` (agent 12.84, user 7.82, rail 7.82).

## Responsive

360 px: strip on two to three rows (tag + label, selector, Métricas); bubbles 80%. ≥ 640 px: strip on one row. ≥ 1024 px: rail, strip, transcript and composer content share the 672 px centered column; backgrounds full width. See [shared/responsive.md](./shared/responsive.md).

## Image resources

| Section | Type | Source | Treatment |
|---|---|---|---|
| Rail + agent avatar | raster concept | `identity/assets/avatar-disc-concept.jpg` (pending SVG) | circle crop, 40 px rail / 32 px groups, `alt=""` |
| Empty state | line drawing (soundhole rosette) | hand-built SVG per imagery-style.md spec | walnut `currentColor`, one honey fill ≤ 20%, `aria-hidden` |
| Product | none | no product photos in the POC | text-only card |

## Related

- [screen-02-warmup.md](./screen-02-warmup.md) · [shared/component-plan.md](./shared/component-plan.md) · [shared/micro-interactions.md](./shared/micro-interactions.md)
