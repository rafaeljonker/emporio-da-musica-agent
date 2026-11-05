# ChatBubble + ChatTranscript — custom spec

> Tier 3 | Brand: emporio-da-musica | Source: `.yml` `constraints.always` (bubbles), STYLE.md "Chat bubbles", identity/brand-applications.md §3

No shadcn equivalent. The transcript is the brand's main surface: spruce for the store's words, walnut for the customer's (Bold Bet 5).

## Anatomy

```
ChatTranscript  <div role="log">
└─ MessageGroup (one per speaker run)
   ├─ Avatar (agent only, once per group, bottom-aligned with the LAST bubble)
   └─ ChatBubble × n  (1–3 per agent reply, arriving sequentially)
       ├─ sr-only speaker prefix ("Assistente:" / "Você:")
       ├─ text (plain, no markdown)
       └─ Timestamp (last bubble of the group only)
```

## Variants

| Variant | Classes | Ratio (L / D) |
|---|---|---|
| `agent` | `max-w-[80%] rounded-2xl bg-card px-4 py-2.5 text-base text-card-foreground` | 9.75 / 12.84 |
| `user` | `ml-auto max-w-[80%] rounded-2xl bg-user-bubble px-4 py-2.5 text-base text-user-bubble-foreground` | 12.50 / 7.82 |

## Sequential grouping

| Position in group | Agent corners | User corners |
|---|---|---|
| single | `rounded-2xl rounded-bl-md` | `rounded-2xl rounded-br-md` |
| first | `rounded-2xl rounded-bl-md` | `rounded-2xl rounded-br-md` |
| middle / last | `rounded-2xl rounded-tl-md rounded-bl-md` | `rounded-2xl rounded-tr-md rounded-br-md` |

- Spacing: `gap-2` (8px) inside a group, `mt-4` (16px) on speaker change.
- Avatar: 32px honey disc (`identity/assets/avatar-disc-concept.jpg`), `alt=""` (the speaker is already named in text), rendered once per agent group; other bubbles get a 32px spacer so text aligns.
- Agent bubbles of one reply are appended one at a time with a short natural delay (backend-driven); each uses `animate-arrive` (fade + 4px rise, 150ms). Under reduced motion they appear instantly. No layout animation.
- Timestamp: 13px `text-muted-foreground tnum`, under the last bubble of a group, `aria-hidden` on the visual and an sr-only full time in the prefix if needed ("Assistente, 14:32:").

## Content rules

- Source Sans 3 400, 16/24. `whitespace-pre-line` for line breaks; no markdown rendering (bold, lists, headers are stripped/never produced).
- Prices inside text use pt-BR format ("R$ 599,90", "R$ 1.967,18"). Structured product info uses [ProductCard](./product-card.md) inside the agent group.
- Fraunces never appears in a bubble.

## ChatTranscript a11y

```tsx
<div
  role="log"
  aria-label="Conversa com o assistente da Empório"
  aria-relevant="additions"
  tabIndex={0}                      /* scrollable region must be keyboard reachable */
  className="flex flex-1 flex-col overflow-y-auto px-4 py-4 focus-visible:outline-2 focus-visible:outline-ring focus-visible:-outline-offset-2"
>
```

- `role="log"` carries implicit `aria-live="polite"`; do not add `aria-live="assertive"` or `role="alert"` to any bubble.
- Append a bubble to the DOM only when its text is complete (no token-by-token streaming into the live region), so each bubble is announced once.
- Every bubble begins with `<span className="sr-only">Assistente: </span>` or `Você: ` so speaker is not conveyed by color or side alone.
- The typing indicator is NOT inside the log (see [typing-indicator.md](./typing-indicator.md)).
- Focus stays in the composer after sending; never move focus into the transcript on new messages.
- Auto-scroll to bottom only if the user is already near the bottom; otherwise show a secondary button "Novas mensagens" that scrolls down.
- Customer switch divider ("Agora conversando como Ana") is a `<p>` inside the log with `role="separator"`-style visuals (1px `border-border` lines + 14px muted text) so it is announced as an addition.

## States

| State | Treatment |
|---|---|
| empty | rosette line drawing + `text-muted-foreground`: "Pergunta de preço, estoque, entrega ou qual instrumento combina com você. Pode mandar." |
| user bubble pending send | normal style; no "sending" spinner |
| send failed | inline line under the user bubble, `text-muted-foreground` 14px: "Perdi o fio da conversa aqui." + link-variant button "Manda de novo?" |

## Copy examples (pt-BR)

- Agent: "Oi, Luísa! Tá procurando violão ou outro instrumento?"
- Agent: "Pro seu nível, o C40 de R$ 599,90 dá conta tranquilo."
- Agent: "Qualquer coisa me chama aqui."
