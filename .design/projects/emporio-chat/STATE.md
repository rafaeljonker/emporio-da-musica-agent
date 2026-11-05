# Design State

## Project: Emporio Chat
**Brand:** emporio-da-musica
**Started:** 2026-11-05
**Current Phase:** 3 (Design complete)
**Prettiness Level:** 45%

---

## Phase Progress

| # | Phase | Status | Started | Completed |
|---|-------|--------|---------|-----------|
| 1 | Brief | complete | 2026-11-05 | 2026-11-05 |
| 2 | Research | skipped | — | — |
| 3 | Design | complete (revision 1) | 2026-11-05 | 2026-11-05 |
| 4 | Critique | complete | 2026-11-05 | 2026-11-05 |
| 5 | Build | pending | — | — |
| 6 | Review | pending | — | — |

## Git

| Field | Value |
|-------|-------|
| Branch | feat/design |
| PR | — |
| Issue | — (no GitHub issue; one PR per project phase) |

## Screen Build Status
<!-- Populated during build phase — tracks per-screen implementation -->

| # | Screen | Build Status | Review Status |
|---|--------|-------------|---------------|
| 1 | Chat (incl. warm-up body state) | pending | pending |
| 2 | Warm-up | pending | pending |
| 3 | Demo login | pending | pending |

<!-- Status: pending | in-progress | complete | needs-revision -->

## Review Loops
<!-- Track critique → fix → re-critique cycles -->

| Loop | Date | Issues Found | Issues Fixed | Resubmitted |
|------|------|-------------|-------------|-------------|
| 1 | 2026-11-05 | 5 critical, 10 high, 6 medium, 20 low | all critical/high/medium; 14 low (+2 partial); 4 [STYLE] deferred | yes (design revision 1) |

## Status Values
<!-- pending | in-progress | complete | needs-revision | skipped -->

## Decisions
- 2026-11-05: Lean GSP path. Project research (phase 2) skipped; next is gsp-project-design.
- 2026-11-05: Warm-up is a body state of the chat shell (wood rail + composer stay), so a message typed during warm-up can be queued and sent automatically.
- 2026-11-05: Warm-up shows a rounded-up expected total ("normalmente leva cerca de N s"), never a countdown; reconciles the spec's "estimated time" with the brand's no-fake-progress rule.
- 2026-11-05: No toast (sonner), no ScrollArea: errors are inline, the transcript is a native overflow `role="log"`.

- 2026-11-05: Design complete (designed from brief only, research skipped). 3 screen chunks, 6 shared chunks, clickable HTML mockups in design/mockups/.
- 2026-11-05: Bubble pacing is backend-driven and length-proportional (`delay_ms`); reduced motion removes animation, not pacing.
- 2026-11-05: Local-CPU notice persists under the demo strip after warm-up.
- DECIDED 2026-11-05: metrics placement is option A (collapsed "Métricas" <details> in the demo strip); keeps the transcript WhatsApp-like. Option B dropped.

- 2026-11-05: Design revision 1 complete: critique fixes applied (see design/INDEX.md § Revision 1). Warm-up status/time are backend-owned (`started_at`, measured p75); pacing: bubble 1 at 0 ms, ≤ 3 s per reply; option B removed everywhere.

## Notes
- `frontend/` does not exist yet; it is created in project phase 5 (Build).
