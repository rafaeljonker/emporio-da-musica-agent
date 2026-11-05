# Guidelines
> Phase: guidelines | Brand: emporio-da-musica | Generated: 2026-11-05

## Core

| File | Description |
|------|-------------|
| [emporio-da-musica.yml](./emporio-da-musica.yml) | Style preset — single source of truth (shadcn-flat tokens, light + dark, intensity, patterns, constraints, effects) |
| [STYLE.md](./STYLE.md) | Agent contract (rendered from .yml + philosophy + bold bets + implementation) |
| [guidelines.html](./guidelines.html) | Visual brand guide (open in browser) |

Generate the shadcn `:root` / `.dark` block:

```bash
node .claude/skills/gsp-brand-guidelines/bin/theme-css.js .design/branding/emporio-da-musica/patterns/emporio-da-musica.yml
```

## Components

| File | Type | Description |
|------|------|-------------|
| [token-mapping.md](./components/token-mapping.md) | mapping | Brand tokens → shadcn/ui + Tailwind v4 (`:root`/`.dark`, brand extensions, `@theme inline`, base layer) |
| [button.md](./components/button.md) | override | Primary hover `#93401F`, settle-press, focus ring with 2px cream gap on terracotta, muted disabled |
| [input.md](./components/input.md) | override | `--input` boundary, paper fill, 16px floor, labels above, chat composer |
| [select.md](./components/select.md) | override | Radix Select trigger/content/items, selection never color-only |
| [chat-bubble.md](./components/chat-bubble.md) | custom | Agent/user bubbles, sequential grouping, avatar once per group, transcript `role="log"` |
| [typing-indicator.md](./components/typing-indicator.md) | custom | Three honey dots, `role="status"` outside the log, static under reduced motion |
| [handoff-bubble.md](./components/handoff-bubble.md) | custom | "Repassado pra equipe" limit-admitted state, calm not error |
| [product-card.md](./components/product-card.md) | custom | Paper card, honest badge, three-part promo rule, PIX line |
| [wood-rail-header.md](./components/wood-rail-header.md) | custom | Walnut header + 3px honey rule, cream focus inside |
| [warmup-status.md](./components/warmup-status.md) | custom | Real backend stages + elapsed timer, `role="status"`, no fake progress |
| [customer-selector.md](./components/customer-selector.md) | custom | "Conversar como…" demo-tool strip using Select, thread reset divider |

## Theme registry

| File | Description |
|------|-------------|
| [emporio-da-musica.theme.json](./emporio-da-musica.theme.json) | shadcn `registry:theme` (OKLCH cssVars light/dark + fonts), emitted after the WCAG 2.2 AA gate passed (83 pairs, 0 failures). Install with `/gsp-brand-apply emporio-da-musica` |
