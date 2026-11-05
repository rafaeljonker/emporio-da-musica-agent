# Strengths to Preserve

> Phase: critique | Project: emporio-chat | Generated: 2026-11-05

## Honesty as an engineering contract

- **The UI never advances a stage on a timer.** `GET /warm/status` is the only source of stage, written into both the brand spec and target-adaptations. This is the rule that makes Bold Bet 3 real; keep it word for word in the build.
- **Count-up, never countdown.** "Esperando há {s} s" plus a static expected total rounded *up* to 10 s. The overrun case can't lie, and "faltam", percentages, bars and spinners are banned explicitly. A good reconciliation of the spec's "estimated time" with the brand.
- **The explanation names the real reason**: "numa GPU só dele no Modal. Quando ninguém está usando, ela desliga pra não gerar custo". Plain language, no disguise, and the variant copy for `local_cpu` is just as frank.
- **Structured flags only.** HandoffBubble, ProductCard and the honest badge render from backend `kind` / `honest_pick` / `promotion`, never inferred from text on the client.

## The warm-up as a body state of the chat shell

Keeping the rail, strip and composer mounted is what makes "type now, it goes when ready" possible and avoids a jarring route change on `ready`. One queued message, sent exactly once, with `Clock` + words. Preserve the architecture even if the panel layout changes.

## Store content vs. demo tooling

Everything the store "says" is on wood/spruce/paper; everything the evaluator drives is in the cream strip behind the `FlaskConical` "Demonstração" tag. Option A keeps the transcript pure WhatsApp. This separation is the project's clearest IA idea.

## Accessibility thought through, not bolted on

- `role="log"` with bubbles appended only when complete, sr "Assistente: " / "Você: " prefixes.
- TypingIndicator `role="status"` outside the log, mounted once, announced once per reply.
- The stage sentence in its own status region so the list can re-render quietly; timer explicitly `aria-live="off"`; failure is the only `role="alert"`.
- Reduced motion removes animation but **keeps pacing** as content timing. A subtle, correct call.
- Focus walnut 2px with a cream gap on terracotta; 44 px targets throughout.

## Brand fidelity

- Terracotta appears only on Entrar, send and Tentar de novo. Bold Bet 1 holds in every mockup.
- Walnut user bubbles vs spruce agent bubbles: speaker is obvious at 360 px without color-only cues.
- The wood rail with its honey rule, the breathing Boca, paper grain on `::before` only, tinted `shadow-sm` on paper sheets. Every effect is from the vocabulary.

## Copy

Authored pt-BR that sounds like the brand: "Entra aí pra conversar com a Empório", "E-mail ou senha não bateram. Confere e tenta de novo.", "Perdi o fio da conversa aqui.", "Afinando o atendimento". Blame-free errors, no em dashes, no emoji, no stock phrases in UI copy. Mockup data is organic: "1.284 de entrada · 96 de saída", "R$ 0,0042", "R$ 806,55 no PIX", "BRJL5544332BR".

## Restraint (YAGNI)

No toast, no ScrollArea, no collapsible install, native `<details>` for metrics, no show-password toggle, one route after login. The mockups are clickable, static, and explicit about what is mockup chrome (`.mk-` prefix).
