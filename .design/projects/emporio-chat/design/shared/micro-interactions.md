# Micro-interactions

> Phase: design | Project: emporio-chat | Generated: 2026-11-05 | Revised: 2026-11-05 (revision 1: pacing, dot color, one breath)
> Effects vocabulary (STYLE.md): warm-darken, settle-press, fade-arrive, ring-breathe, dot-pulse. Nothing outside this list. Easing `--ease-brand: cubic-bezier(0.33, 1, 0.68, 1)`.

## Table

| Trigger | Technique | Animation | Duration | Easing | Reduced motion |
|---|---|---|---|---|---|
| Hover primary (Entrar, send, retry) | warm-darken | bg `#A54A29` → `#93401F` | 150 ms | brand | color change kept (not motion) |
| Active primary | settle-press | `#93401F` + `scale(.98)` | 100 ms | brand | no scale |
| Hover secondary / ghost (Sair) | warm-darken | gains spruce fill (rail: cream 10%) | 150 ms | brand | kept |
| Link hover (Manda de novo?) | underline-thicken | 1 → 2 px underline | instant | — | kept |
| Agent bubble arrives | fade-arrive | opacity 0 → 1, translateY 4 → 0 | 150 ms | brand | appears instantly |
| User bubble sent | fade-arrive | same | 150 ms | brand | instant |
| Agent composing | dot-pulse | 3 dots (`--muted-foreground` light 5.03:1 on spruce; honey `#E0A94F` dark 7.32:1), opacity .5 ↔ 1, stagger 0/.15/.3 s | 1.2 s loop | ease | static dots, full opacity |
| Warm-up arrival | ring-breathe | Boca scale 1 → 1.04, opacity → .85 | 4 s, **one iteration** (SC 2.2.2: under 5 s; stages + timer already show activity) | ease-in-out | static |
| Stage change, metrics open, divider, queued line, pinned status line | none | — | — | — | — |

No layout animation, no scroll-linked effects, no animated grain, no spinner anywhere.

## Bubble pacing (resolved)

- The backend decides pacing and sends `delay_ms` per bubble; the client waits `delay_ms` with the typing indicator visible, then appends the bubble. No client-side invented delay beyond honoring that value.
- **Bubble 1: `delay_ms = 0`.** The typing indicator has been visible for the whole generation; the first bubble appears the moment the answer is ready.
- **Bubbles 2 and 3** only: `delay_ms = clamp(400 + 22 × chars, 700, 2400)` (ProductCard uses the 700 ms floor).
- **Cap: 3 000 ms of pacing per reply** in total; when the cap is reached, the remaining bubble's delay is cut to what is left (possibly 0).
- Typing indicator stays on between bubbles of one reply (no flicker), announced once.
- Reduced motion does **not** remove pacing: it is content timing, not animation. Under reduced motion only the fade and dot pulse go.
- Honest numbers: the metrics show both "2,4 s no modelo" (server time) and "4,1 s na tela" (send → last bubble, incl. pacing); the warm-up claim "a primeira mensagem sai em uns 2 s" refers to bubble 1, which carries no pacing.

## Gestures and keys

| Input | Result |
|---|---|
| Enter | send; Shift+Enter new line |
| Esc in Select | close list (Radix) |
| Tab | rail → strip → log (scrollable, `tabIndex=0`) → composer |
| Touch scroll up in log | auto-scroll pauses; "Novas mensagens" pill appears on new bubbles |

## Related
- [../screen-01-chat.md](../screen-01-chat.md) · [../screen-02-warmup.md](../screen-02-warmup.md)
