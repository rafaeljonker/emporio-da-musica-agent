# TypingIndicator — custom spec

> Tier 3 | Brand: emporio-da-musica | Source: `.yml` `effects.ambient` (dot-pulse), STYLE.md Animation Recipes

## Anatomy

Agent-style bubble (spruce, `rounded-2xl rounded-bl-md`, `px-4 py-3`) in the agent column (avatar spacer on the left) containing three 6px honey dots (`bg-brand`) with 4px gaps.

## Tokens

| Part | Token | Note |
|---|---|---|
| bubble | `bg-card` | same as agent bubble |
| dots | `--brand` honey | decorative (2.09 on spruce light, 7.32 dark); meaning is carried by the sr-only text, so 1.4.11 does not apply |
| motion | `dot` keyframes 1.2s, stagger 0 / .15s / .3s | `.typing-dot` recipe in STYLE.md |

## States

| State | Treatment |
|---|---|
| visible | while the backend reports the agent is composing, or between sequential bubbles of one reply |
| reduced motion | animation off, dots at full opacity (static) |
| hidden | removed, not faded; no lingering empty bubble |

## A11y

```tsx
<div role="status" className="...">                 {/* sibling AFTER the role="log", not inside it */}
  <span className="sr-only">O assistente está digitando</span>
  <span aria-hidden className="flex gap-1"><i className="typing-dot" /><i className="typing-dot" /><i className="typing-dot" /></span>
</div>
```

- Keep the `role="status"` element mounted for the whole chat session and toggle only its text content: live regions must exist before their content changes to be announced reliably.
- Announce once per reply, not between each sequential bubble (keep the text unchanged while it stays visible).
- Never a spinner; never the word "Carregando".

## Copy

sr-only: "O assistente está digitando".
