# Prioritized Fixes

> Phase: critique | Project: emporio-chat | Generated: 2026-11-05
> Source: [critique.md](./critique.md) · Accessibility: `accessibility-fixes.md` (auditor) · `[STYLE]` = brand-level, route to `/gsp-brand-refine`; untagged = screen-level.
> Metrics placement is option A (owner decision). Option B is dropped and every fix below assumes A.

## Critical (must fix before phase 5 build)

1. **Warm-up status below the fold on phones** ([screen-02-warmup.md](../design/screen-02-warmup.md)). At 360×640 the ~670 px panel starts the stage list ~290 px down a ~366 px body. Change the mobile order (`< md`) to: h2 → stage list → "Esperando há {s} s" → "Normalmente leva cerca de {N} s." → explanation → one combined note. Boca 48 px on mobile (72 at `md+`), `py-6`. Merge "Com a máquina sempre ligada…" and "Pode ir escrevendo…" into one 14px muted paragraph. Once a message is queued, show the panel as a single compact line above the log (`Cpu` icon + "Carregando o modelo · 18 s", not live, plus the existing sr stage sentence) so the status survives the scroll and the open keyboard.

2. **Make warm-up status and time come only from the backend** (screen-02 § States, target-adaptations WarmupStatus):
   - Drop "before the first status response the first stage is shown as current". Return `{ mode, stage, started_at, expected_seconds }` in the `/auth/login` response so the first frame is right (no GPU list in `local_cpu`, no warm-up flash in `provider_api`). If that is not possible, show only the h2 + "Verificando o assistente…" with no stage list until the first poll.
   - Elapsed = `now - started_at` from the backend, so a reload or retry never resets to 0 s.
   - `expected_seconds` = measured p75 of recent cold starts (config written by the deploy measurement), never the 30 s target.
   - Poll failures are not `failed`: after 3 consecutive network errors show "Não consegui falar com o servidor agora. Confere a conexão." and keep polling. On recovery, remove the line.
   - Long wait: drop the primary "Tentar de novo"; copy "Tá demorando mais que o normal. Ainda está em: {current stage}. Pode esperar, a mensagem que você escrever vai assim que ficar pronto." Retry (primary) only on `failed`.

3. **Bubble pacing vs. the "2 s" claim and the metrics** ([shared/micro-interactions.md](../design/shared/micro-interactions.md) § Bubble pacing). First bubble `delay_ms = 0`: typing has already been visible for the whole generation. Pace only bubbles 2 and 3 with the same formula, capped at 3 000 ms total per reply. In the metrics panel, show both numbers: "Tempo: 2,4 s no modelo · 4,1 s na tela". On the warm-up, change the copy to "Com a máquina já ligada, a primeira mensagem sai em uns 2 s." so the claim matches what the evaluator times.

4. **Remove option B from every artifact** (list with line refs in [critique.md § 8](./critique.md)). Rewrite screen-01 "§ Metrics: two options…" as "§ Metrics (option A)" and delete Option B, the Pros/Cons comparison and "Recommendation for the owner: B…". Strip "(B)", "(i)" and "(option A or B)" from screen-01's layout, components, SSE and interactions tables, and from INDEX.md, component-plan, information-architecture, navigation, responsive, personas and exports/INDEX.md. Replace INDEX.md "Open decision for the owner" with "Decided: option A (2026-11-05)". Mockups: delete gallery entry 3b, the A/B toggle buttons in chat.html, `.info-btn`/`.turn-metrics` rendering in mockup.js and the `.info-btn`/`[data-metrics]` rules in mockup.css.

5. **14px interactive text (brand never-rule; causes the brand contract auto-Fail).** Set the "Métricas" `<summary>` to 16px 600 (`text-base`); the panel body can stay 14px. Set the "Manda de novo?" link button to 16px (`text-base`, not `font: inherit` from the 14px error line).

## Important (high priority)

1. **Selector change must not destroy the test.** Keep the previous turns above the divider "Agora conversando como Ana" (dimmed via `text-muted-foreground` is not needed, the divider explains it); start a new session id below. No confirm dialog. During warm-up, insert the divider above the queued bubble and change its line to "Vai como Ana assim que o assistente ficar pronto".

2. **Make option A worth opening** (screen-01 § Metrics):
   - The summary carries the last turn's numbers: "Métricas · 2,4 s · R$ 0,0042" (16px; values `tnum`), so the panel doesn't have to be opened every turn.
   - Panel: "Última resposta" block + a compact history list "Resposta 3 · 2,4 s · R$ 0,0042 · busca no catálogo" (one line per turn, newest first). The tool/handoff word comes from the backend `metrics` event, which fixes the "map it from memory" con.
   - "Sessão" adds "Aquecimento: 31 s" after `ready` (the measured cold start, which backs up the warm-up's honesty).
   - Cost basis line under Custo: "Estimado: segundos de GPU × preço do Modal". In `local_cpu`: "R$ 0 (rodando na sua máquina)".
   - Mobile: open panel `max-h-[40dvh] overflow-y-auto` so it never takes over the transcript.
   - Rename "guarda" to "filtro" (or "guardrail").

3. **Queued message control and announcements** (screen-02 § States). Add a link button "Desfazer" (16px) under the queued bubble that puts the text back in the composer. Later sends during warm-up render as a new bubble in the same group (a log addition, announced) and are flushed as one message joined by `\n`. On flush, set the TypingIndicator status text, which already announces activity; do not mutate the old line silently. Persist the queued text in `sessionStorage` across reload. On session expiry while queued, keep the text in `sessionStorage` and restore it in the composer after re-login.

4. **Partial reply error** (screen-01 § States / SSE). An `error` after ≥ 1 agent bubble: typing off, line under the agent group "Perdi o fio no meio da resposta." + "Manda de novo?" (resends the user's last message once). Never remove the bubbles already shown.

5. **No forced keyboard on `ready`** (screen-02 § Ready, screen-01 § Accessibility). Move focus to the composer only if `matchMedia("(pointer: fine)")` or if the composer already had focus. This matches the login rule "focus not forced (avoids keyboard pop on mobile)".

6. **HandoffBubble honesty** ([handoff-bubble.md](../../../branding/emporio-da-musica/patterns/components/handoff-bubble.md) usage). The label should state what the system did, not repeat the body: "Repassado pra equipe" (`UserRound`) / "Retorno em até 24 horas úteis" (`Clock`), driven by the backend flag. The metrics history line shows "repasse registrado", so the evaluator can see the handoff tool fired even though nobody will "já te retorno" in a demo.

7. **Explain the demo strip once.** In the chat empty state, under the existing line, add 14px muted: "Na faixa de demonstração, \"Conversar como…\" simula quem manda mensagem pelo WhatsApp." Keep the Radix item second line "o assistente vai pedir o número do pedido" for "Sem identificação".

8. **Login sets the expectation.** Replace the demo note with: "Ambiente de demonstração. As credenciais foram enviadas no e-mail da entrega. Ao entrar, o assistente começa a ligar; na primeira vez leva uns {N} s." ({N} = same measured value as the warm-up.)

9. **Desktop alignment** ([shared/responsive.md](../design/shared/responsive.md)). Rail and strip backgrounds span full width; their *content* sits in the same `mx-auto max-w-2xl px-4` column as the transcript, so the selector and Métricas line up with the conversation at 1280 px.

## Polish (if time allows)

1. ProductCard name: `<p id>` + `aria-labelledby` instead of `<h3>` (the chat state has no `<h2>`).
2. Mockup agent copy: "No violão em si, tô aqui pra ajudar." → "Se for violão, é comigo." (avoids the banned "estou aqui para ajudar" pattern).
3. Drop the parenthetical in the production line: "(normalmente 2,2 s)".
4. Warm-up: show the type-ahead message once (keep the placeholder "Pode ir escrevendo"; the note merges per Critical 1).
5. Build notes from mockup drift: Fontsource, not Google Fonts; auto-scroll only when near the bottom + "Novas mensagens"; `overflow-wrap: anywhere` on bubbles; login empty-submit focuses the first empty field.
6. Dark mode: hide the raster wordmark plate (show the Fraunces h1 only) until the SVG logo lands.
7. Long wait > 5 min in `local_cpu`: no change needed; confirm the threshold uses the local `expected_seconds`.
8. `[STYLE]` Clarify that the .05 canvas grain and the login wood bands are exempt from "no texture behind text under 18px".
9. `[STYLE]` Align selector label size (14px in customer-selector.md vs 16px Input label rule); recommend 16px.
10. `[STYLE]` Add `underline-thicken` to the interaction vocabulary, or remove it from the hover table.
11. `[STYLE]` Document the chat composer as the one placeholder + `aria-label` exception to "never placeholder-only".
