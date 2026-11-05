# CustomerSelector ("Conversar como…") — custom spec

> Tier 3 | Brand: emporio-da-musica | Source: identity/brand-applications.md §4 | Composes [select.md](./select.md)

A demo control that picks which customer from `data/customers.csv` the user is impersonating. It must look like a tool, not like store content.

## Placement and demo-tool styling

- A thin **demo strip** directly under the wood rail: `flex items-center gap-2 border-b border-border bg-background px-4 py-2`.
- Leading tag: `FlaskConical` 16px + "Demonstração", 14px 600 `text-muted-foreground` (6.45). No honey, no terracotta (choosing is not the primary action).
- Then the Select (brand override) with a compact trigger: `h-11 min-w-48 rounded-md border-input bg-popover`.
- Not in the rail itself, so rail focus/contrast rules stay simple; on `md+` the strip can sit right-aligned.

## Anatomy

```
DemoStrip
├─ tag: FlaskConical + "Demonstração"
├─ <Label> "Conversar como…"   (visible, 14px 600 muted; or sr-only on narrow screens with the trigger showing "Conversar como: Ana")
└─ Select
   ├─ Trigger: "Ana Carolina Ferreira"  + ChevronDown
   └─ Content: one item per customer
       ├─ first line  name, 16px 600 walnut
       └─ second line city (or last order), 14px muted
```

## Item states

| State | Treatment |
|---|---|
| rest | paper row, `min-h-11` |
| highlighted (keyboard/hover) | honey fill + walnut text (4.66 / 8.45) |
| selected | walnut 1px outline (`ring-1 ring-ring ring-inset`) + `Check` icon + 4px honey left marker + semibold. Never color alone. |
| current customer reopened | the selected item has focus on open (Radix default) |

## Behavior

- Changing customer resets the thread: clear messages, then append to the transcript log a quiet divider "Agora conversando como {primeiro nome}" (1px `border-border` lines either side, 14px `text-muted-foreground`, centered). The log announces it politely.
- No confirmation dialog (demo tool). Focus returns to the composer after selection.
- The selected customer id is sent with each request as demo context; the UI does not show phone or e-mail (no PII on screen beyond name and city).

## A11y

- Visible label "Conversar como…" (or `aria-label="Conversar como"` on the trigger when the label is sr-only).
- Radix Select provides combobox/listbox semantics, typeahead and Escape.
- The "Demonstração" tag is plain text, read before the control.
- Targets ≥ 44px; brand focus outline.

## Copy (pt-BR)

Label "Conversar como…" · tag "Demonstração" · item "Lucas Mendes da Silva" / "Campo Grande" · divider "Agora conversando como Lucas".
