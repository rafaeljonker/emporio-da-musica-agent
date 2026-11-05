# Information Architecture

> Phase: design | Project: emporio-chat | Generated: 2026-11-05

## Hierarchy

```
Demo login (/)                       unauthenticated
└─ Chat shell (/chat)                authenticated; one route
   ├─ WoodRailHeader                 store identity · Sair
   ├─ DemoStrip                      demo tools (look like tools, not content)
   │  ├─ "Demonstração" tag
   │  ├─ CustomerSelector            Sem identificação | customers from /customers
   │  └─ Métricas (<details>: session totals, last reply, history)
   ├─ LocalModeNotice                mode = local_cpu only
   ├─ StatusRegion                  persistent sr-only role=status (warm-up + undo)
   ├─ Body (one of)
   │  ├─ WarmupStatus                mode ≠ provider_api and stage ≠ ready
   │  └─ Transcript                  empty state | groups | divider | typing
   │     └─ per agent turn: bubbles, ProductCard, HandoffBubble
   └─ Composer                       always present
```

## Grouping rationale

- **Store content vs demo tooling.** Everything the store "says" (rail identity, bubbles, cards) lives on wood/spruce/paper. Everything the evaluator uses to drive the demo lives in the cream demo strip with the `FlaskConical` "Demonstração" tag, so the two never blur.
- **Warm-up is a body state, not a route.** Keeps the shell (and composer) mounted, which is what makes the queued message possible and avoids a jarring screen change on `ready`.
- **One route after login.** No settings, history or profile: out of scope. Customer identity is a demo control, not navigation.
- **Metrics are secondary.** Collapsed by default in the demo strip; the summary carries session totals so it rarely needs opening; never shown inside a bubble.
- **Heading model.** h1 = rail; h2 = warm-up title only. Chat content (ProductCard name, metrics block titles) uses `<p>` with `aria-labelledby` / `<strong>`, so no level is skipped.

## Data shown per object

| Object | Shown | Never shown |
|---|---|---|
| Customer (selector) | full name, city | phone, e-mail, id |
| Product (card) | name, honest badge (flag), price, PIX price or promo line | stock count, SKU |
| Order (agent text) | number, item, status, tracking, estimated date | other customers' orders |
| Metrics | tokens in/out, time on model and on screen, latency per stage, cost R$ + basis, session totals, warm-up time, per-turn action word | trace ids, prompts |

## Related
- [navigation.md](./navigation.md) · [../screen-01-chat.md](../screen-01-chat.md)
