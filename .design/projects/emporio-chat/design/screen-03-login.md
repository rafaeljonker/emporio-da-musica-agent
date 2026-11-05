# Screen 03: Demo login

> Phase: design | Project: emporio-chat | Generated: 2026-11-05 | Revised: 2026-11-05 (revision 1)
> Brand: [brand-applications.md §1](../../../branding/emporio-da-musica/identity/brand-applications.md) · [input.md](../../../branding/emporio-da-musica/patterns/components/input.md) · Mockup: [mockups/login.html](./mockups/login.html)
> Revision 1: demo note sets the warm-up expectation; login response carries the warm status; "Entrando…" status region; `aria-invalid` only for field errors; empty submit focuses the first empty field; wordmark hidden in dark mode.

## Purpose

Gate the hosted demo (no GPU spend on anonymous visits) and start the warm-up the instant credentials are accepted. Feel: opening the shop door, not logging into a bank. The one editorial moment of the product (variance dial 3).

## User flow position

Entry point. `POST /auth/login` ok (response includes `{ mode, stage, started_at, expected_seconds }`, so the shell's first frame is right) → `POST /warm` (fire and forget) → chat shell (screen 02 body). Opening the page triggers nothing.

## Layout

```
cream canvas + paper grain + rosette tile 4%
        [ wordmark concept image ]        max 300 px wide, 16:7 crop, centered
   Entra aí pra conversar com a Empório   h1, Fraunces 600, balanced
          A verdade de quem toca.         .tagline (Fraunces italic, muted)
  ┌──────────────────────────────────┐
  │ E-mail                           │    spruce card + wood grain, p-6 / md:p-8
  │ [______________________________] │    label above, paper field, 44 px
  │ Senha                            │
  │ [______________________________] │
  │ (error line, role="alert")       │
  │ [            Entrar            ] │    full-width terracotta pill
  └──────────────────────────────────┘
 Ambiente de demonstração. As credenciais foram enviadas no e-mail da entrega.
 Ao entrar, o assistente começa a ligar; na primeira vez leva uns {N} s.
```

{N} = `ceil10(expected_seconds)` from config, the same measured p75 the warm-up shows.

- `max-w-md` column; mobile: top-aligned with `pt-8`; `md+`: vertically centered.
- No header, no rail (the rail belongs to chat screens).

## Components

shadcn `card` (`.surface-wood`), `label` + `input` (brand override), `button` primary. Wordmark is an `<img>` of `logo-wordmark-concept.jpg` with `alt="Empório da Música"` until the vector logo lands.

## States

| State | Treatment |
|---|---|
| Default | empty fields, focus not forced (avoids keyboard pop on mobile) |
| Empty submit | `role="alert"` "Preenche o e-mail e a senha pra entrar." focus to first empty field |
| Loading | button label "Entrando…", `aria-busy="true"`, plus an sr-only `role="status"` set to "Entrando…" (cleared on fail); repeated submits ignored; no spinner |
| Error (401) | `CircleAlert` 20px + "E-mail ou senha não bateram. Confere e tenta de novo." in oxblood; both fields `aria-invalid` (cleared on input), `aria-describedby` the line; focus to e-mail; values kept |
| Error (network / 5xx) | "Não consegui falar com o servidor agora. Confere a conexão e tenta de novo." Fields are **not** marked `aria-invalid` (they are not the problem) |
| Success | navigate to chat shell; warm-up already requested |

## Interactions

Enter submits. Button warm-darken on hover, settle-press on active. Password managers supported (`autocomplete="username"` / `current-password`). No "show password" toggle (YAGNI for a demo; add if critique asks).

## Accessibility

- Order: wordmark → h1 → tagline → E-mail → Senha → error → Entrar → demo note.
- Labels visible above fields, 16px; never placeholder-only.
- Error line is `role="alert"`, linked with `aria-describedby`; words + icon, never color alone.
- Primary focus adds a 2px cream gap so walnut never touches terracotta.
- `lang="pt-BR"` on the document.

## Responsive

360 px: card full width minus 16 px gutters, wordmark ~250 px. ≥ 768 px: card `p-8`, column centered vertically. Dark mode: the raster wordmark (cream plate) is hidden; the Fraunces h1 carries the name until the SVG logo lands.

## Image resources

| Section | Type | Source | Treatment |
|---|---|---|---|
| Wordmark | raster concept | `identity/assets/logo-wordmark-concept.jpg` | `object-fit: cover`, 16:7 crop (trims the empty margin) |
| Canvas | texture | paper grain + rosette tile 4% | off under reduced data / dark |
| Card | texture | `.surface-wood` bands | behind text only via `::before`; contrast unchanged |

## Related

- [screen-02-warmup.md](./screen-02-warmup.md) · [shared/navigation.md](./shared/navigation.md)
