# Alternative Directions

> Phase: critique | Project: emporio-chat | Generated: 2026-11-05
> Both directions keep the brand law (STYLE.md) and the owner's metrics decision rationale: the transcript stays pure store conversation. Neither brings back option B (per-turn controls in the transcript).

## Direction 1: "Balcão já aberto" (the warm-up lives in the conversation)

**Idea.** Remove the warm-up panel. From the first frame the body is the transcript. One quiet status card is pinned at the top of the log, styled as a demo/system object (cream, 1px `border` hairline, `FlaskConical`-free, 14px muted + 16px current stage), not as a spruce store bubble. It holds the h2-level line "Afinando o atendimento", the current stage, "Esperando há 18 s" and "Normalmente leva cerca de 30 s". A "Por quê?" disclosure (native `<details>`) holds the Gemma / Modal explanation. The composer is live; queued messages sit directly under the card. On `ready` the card shrinks to one line, "Pronto · aquecimento levou 31 s", and stays as the first entry of the log.

**Why.** It solves the mobile fold problem by construction: the status is ~120 px instead of ~670 px. It makes the queue obvious (your message is right below the status), and the cold start stays visible after the fact, which is honest.

**Trade-offs.**
- (+) Best phone experience; no body-state switch; one fewer layout to build.
- (+) The warm-up duration becomes evidence instead of disappearing.
- (−) Bold Bet 3 loses its stage: no breathing Boca at 72 px, no Fraunces moment, no tuning pegs. The warm-up becomes a status, not a scene.
- (−) It risks blurring "store speaks" vs "system speaks" if the card ever drifts toward spruce. Needs a firm rule: system objects are cream + hairline, never spruce.
- Brand impact: STYLE Bold Bet 3 would need a `/gsp-brand-refine` amendment ("honest warm-up" as a pinned status card).

## Direction 2: "Bancada do avaliador" (evaluator workbench on desktop)

**Idea.** Design for the primary persona's real viewport. At `lg+`, the screen splits: the chat at phone width (~420 px column, rail on top) on the left, framed by the cream canvas, and on the right a **"Bastidores"** panel (`bg-popover`, hairline, 14px, `tnum`). It shows a per-turn trace: user message excerpt → tools called (catálogo, pedidos, políticas) → handoff/honest flags → latency per stage → cost; plus the warm-up timeline and session totals. The demo strip (tag + "Conversar como…") moves into the top of Bastidores. Below `lg` it collapses into option A exactly as designed (strip + `<details>`).

**Why.** The evaluator judges "lógica, clareza e iniciativa" and tool accuracy. Seeing which tool backed each answer turns the metrics from numbers into proof. The transcript stays 100% WhatsApp, so the reason the owner dropped B (controls inside the conversation) still holds.

**Trade-offs.**
- (+) Strongest evaluator story; per-turn mapping without recall; the phone-width chat shows the customer experience at a glance.
- (+) Makes the honesty brand visible at system level (every number traceable).
- (−) More build: a second panel, a richer `metrics` SSE event (tool names, flags). The phase 5 window (07–08/11) is tight.
- (−) Dashboard gravity: it can make the agent feel like a pipeline rather than a person at the counter, which works against the heartbeat. Mitigate by keeping Bastidores collapsible and closed by default for anyone who isn't the evaluator.
- (−) Two layouts to keep consistent (lg split vs. A on mobile).

## Recommendation

Keep the current direction and apply the Critical fixes. Borrow from Direction 1 the **compact pinned status after a message is queued** (already Critical 1) and from Direction 2 the **one-line per-turn history inside option A** (Important 2). Both get most of each direction's value at a fraction of the build cost.
