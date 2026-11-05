# Navigation

> Phase: design | Project: emporio-chat | Generated: 2026-11-05

## Type

**Single-screen app with a header (wood rail).** No tab bar, sidebar or hamburger: there is one destination after login. Justification: the product is one conversation; any nav chrome would dilute the WhatsApp feel (variance dial 3).

## Primary nav

| Item | Where | Behavior |
|---|---|---|
| Entrar | login card | → chat shell (warm-up body when needed) |
| Sair | wood rail, right; ghost button `LogOut` + "Sair" | clears the demo session → login |

## Secondary (in-page controls, not navigation)

| Control | Where |
|---|---|
| Conversar como… | demo strip |
| Métricas | demo strip (collapsed `<details>`) |
| Novas mensagens | floating above composer when scrolled up |

## Routing and guards

- `/` login; `/chat` shell. Unauthenticated `/chat` → `/`. Authenticated `/` → `/chat`.
- Browser back from `/chat` goes to whatever was before (system back is never overridden); session persists until Sair or expiry. Expired session on any call → login with the line "Sua sessão expirou. Entra de novo pra continuar." A queued message survives in `sessionStorage` and returns to the composer after re-login.
- Reloading `/chat` re-polls `/warm/status`; elapsed time continues from the backend's `started_at`; a queued message is restored from `sessionStorage`. If already `ready`, chat shows immediately (thread is not persisted across reloads in the POC).

## Responsive behavior

Same structure at every width. Rail full width; "Sair" keeps its visible text at 360 px (fits next to the 2-line identity block). The demo strip wraps below 640 px. At ≥ 1024 px rail and strip content sit in the transcript's 672 px column.

## Related
- [information-architecture.md](./information-architecture.md) · [responsive.md](./responsive.md)
