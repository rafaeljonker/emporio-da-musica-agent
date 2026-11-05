# Select — override spec (shadcn `select`, Radix)

> Tier 2 | Brand: emporio-da-musica | Consumer: [customer-selector.md](./customer-selector.md)

## Why override

- Radix highlight uses `focus:bg-accent focus:text-accent-foreground`. With the brand tokens this is honey + walnut (4.66 light / 8.45 dark), which passes, so the highlight stays token-driven. What changes:
- Trigger needs the field boundary (`border-input`), paper fill, 44px height and the brand focus outline (shadcn uses a 3px ring at 50%).
- `SelectItem` check indicator must be visible and paired with text weight so selection is never honey-only (honey vs cream is 2.68).
- Content surface uses `bg-popover shadow-md rounded-lg` (12px) instead of `rounded-md`.

## Anatomy

| Part | Classes |
|---|---|
| `SelectTrigger` | `h-11 rounded-md border border-input bg-popover px-3 text-base text-foreground gap-2 focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2 focus-visible:ring-0 data-[placeholder]:text-muted-foreground` |
| chevron | `ChevronDown` 16px, `text-muted-foreground`, `aria-hidden` |
| `SelectContent` | `bg-popover text-popover-foreground rounded-lg border border-border shadow-md` (hairline is decorative; the shadow and fill separate it) |
| `SelectItem` | `min-h-11 rounded-sm py-2 pl-3 pr-8 text-base data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground data-[state=checked]:font-semibold` |
| `SelectItemIndicator` | `Check` 16px walnut (current color), right side |
| `SelectLabel` | 14px 600 `text-muted-foreground`, sentence case |

## States

| State | Treatment |
|---|---|
| trigger rest / open | `--input` border; `aria-expanded` from Radix |
| trigger focus-visible | 2px walnut outline, 2px offset (cream outline inside the wood rail) |
| item highlighted (keyboard/hover) | honey fill, walnut text (4.66) |
| item checked | `Check` icon + semibold text (not color alone) |
| disabled item | `text-muted-foreground`, `aria-disabled` from Radix |

## A11y

- Always paired with a visible `Label` or the trigger's visible text ("Conversar como…"); Radix supplies `role="combobox"` / `listbox` / `option`, typeahead and Escape.
- Item text is the accessible name; secondary context lines go inside the same item (they are read together).
- Do not put terracotta anywhere in the Select: choosing is not the primary action of the view.
