# HandoffBubble — custom spec

> Tier 3 | Brand: emporio-da-musica | Source: `.yml` `patterns.bubble-handoff`, constraint "unknown fact = handoff"

The Sage "truth" moment: the agent admits a limit or hands off to staff. Calm, not an error.

## Anatomy

A normal agent [ChatBubble](./chat-bubble.md) (same grouping, avatar, corners) with one extra first line:

1. Label row: Lucide `UserRound` (or `Clock` when a return time is promised) 16px + label text, 14px 600 `text-muted-foreground` (5.03 on spruce, 7.98 dark), `gap-1.5`, `mb-1`.
2. Body: the message, standard bubble text.

## Tokens

`bg-card`, `text-card-foreground`, `text-muted-foreground`. Nothing else: no border, tint, honey fill, terracotta (not clickable), oxblood or `CircleAlert` (not an error), no spinner, no shake.

## States

| Variant | Icon | Label | Body example |
|---|---|---|---|
| confirm with team | `UserRound` | "Repassado pra equipe" | "Isso eu preciso confirmar com a equipe. Já deixei registrado pra eles." |
| promised return time | `Clock` | "Retorno em até 24 horas úteis" | "Poxa, entendo a chateação. Já registrei e alguém da loja te responde em até 24 horas úteis." |

Trigger: a structured flag from the backend (e.g. `message.kind === "handoff"`), never inferred from text on the client.

## A11y

- The label is visible text, read as part of the bubble: "Assistente: Repassado pra equipe. Isso eu preciso confirmar…".
- Announced like any message through the transcript `role="log"`; no `role="alert"`, no assertive live region.
- Icon `aria-hidden`.

## Code hint

```tsx
<ChatBubble variant="agent">
  <span className="mb-1 flex items-center gap-1.5 text-sm font-semibold text-muted-foreground">
    <UserRound size={16} strokeWidth={1.75} absoluteStrokeWidth aria-hidden />
    Repassado pra equipe
  </span>
  Isso eu preciso confirmar com a equipe. Já deixei registrado pra eles.
</ChatBubble>
```
