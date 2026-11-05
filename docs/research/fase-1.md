# Phase 1 research: design of the Empório da Música chat

Date: 2026-11-05. Scope: GSP, chat patterns, long waits, accessibility, design tokens.

## 1. Get Shit Pretty (GSP)

**Installation (README):** https://github.com/jubscodes/get-shit-pretty
- The README documents `pnpm dlx get-shit-pretty` or `bunx get-shit-pretty`. `npx get-shit-pretty` appears in the local SKILL (`~/.claude/skills/get-shit-pretty/SKILL.md`), but the README, as I read it, does not mention it. I did not confirm that it works.
- The installer is **interactive** (it asks for runtime and global/local). There is a non-interactive mode: `--claude --global` or `--claude --local` (README).
- Global writes to `~/.claude/` (skills in `~/.claude/skills/`, agents in `~/.claude/agents/`). The README does not say the installer creates files in the project. Design artifacts go to `.design/` in the project (`~/.claude/skills/get-shit-pretty/SKILL.md`).
- The README does not define a "lean path". The closest is `/gsp-style <preset>`, which generates tokens without the branding diamond.

**Local state (verified):** the `gsp-*` skills exist in `~/.claude/skills/`, along with `~/.claude/references/`, `prompts/` and `templates/`. But `~/.claude/agents/` is **empty** and there is no `gsp-brand-strategist*` in `~/.claude`. The SKILLs say "GSP requires a full installation to work — agents, prompts, templates" (`~/.claude/skills/get-shit-pretty/SKILL.md`). Strategy, identity, patterns, design and critique spawn agents (`gsp-brand-strategist`, `gsp-identity-designer`, `gsp-system-architect`, `gsp-designer`, `gsp-critic`, `gsp-accessibility-auditor`; see the `<objective>` of each SKILL.md in `~/.claude/skills/gsp-*/SKILL.md`). Conclusion: the local installation looks incomplete. This is an inference; I did not try running a skill.

**Lean path order (local SKILLs):**
1. `/gsp:start`: creates `.design/branding/{brand}/BRIEF.md` and `.design/projects/{project}/` (`~/.claude/skills/gsp-start/SKILL.md`). Interactive (uses `AskUserQuestion`).
2. `/gsp:brand-strategy`: generates `strategy/` with 5 chunks (includes `voice-and-tone.md`). Interactive. Reads `discover/` if it exists; runs with only the BRIEF.md (`gsp-brand-strategy/SKILL.md`), so `brand-research` can be skipped.
3. `/gsp:brand-identity`: generates `identity/` (6 chunks + `palettes.json`). Requires the complete strategy (`gsp-brand-identity/SKILL.md`).
4. `/gsp:brand-patterns`: generates `system/` with `tokens.json`, foundations, components and `preview.html` (`gsp-brand-patterns/SKILL.md`).
5. `/gsp:project-brief`: generates `projects/{p}/brief/` (`gsp-project-brief/SKILL.md`).
6. `/gsp:project-design`: generates `projects/{p}/design/` (one chunk per screen) (`gsp-project-design/SKILL.md`).
7. `/gsp:project-critique`: runs `gsp-critic` (Nielsen) and `gsp-accessibility-auditor` (WCAG 2.2 AA) in parallel and writes to `critique/` (`gsp-project-critique/SKILL.md`). If there is `needs-revision`, `project-design` rereads `critique/prioritized-fixes.md`.

Prerequisite: `brief` and `design` read `brand.ref` and `system/tokens.json`. That is why patterns cannot be skipped, unless `/gsp:style` is used (`gsp-style/SKILL.md`). Note: the README uses `/gsp-...` names, the local SKILLs use `/gsp:...`. Confirm with `/gsp-help`.

## 2. Chat UI patterns

I did not find an authoritative source for bubble layout. The recommendations below are market convention and my inference.
- Layout: customer bubbles on the right and attendant bubbles on the left, grouping of consecutive messages from the same sender, a timestamp per group, mobile-first with the input fixed at the bottom. WhatsApp convention, not citable.
- **Pacing:** there is no validated benchmark. Sources for the finding: vendors use a fixed delay (default 2 s, https://support.ingenious.ai/hc/en-au/articles/5114874768407), a delay scaled to message length with a minimum and a maximum (https://help.nicecxone.com/content/aiassistantsandbots/botbuilder/featuredetails/smarttyping.htm) and the open source WhatsApp presence module models 42 wpm plus random jitter (https://cdn.jsdelivr.net/npm/waha-openclaw-channel@2.2.0/docs/presence.md). 42 wpm is about 3.5 characters per second (my calculation, 5 characters per word). The research recommends a delay proportional to length, with a floor and a ceiling, and random variation, all to be calibrated in testing.
- The NN/g chatbot page (`/articles/chatbots-ux-heuristics/`) returned 404, so there is no NN/g source on this.

## 3. Long waits (cold start from 30 s to 3 min)

- The 10 s limit is "the maximum the user keeps their attention". Above that: show percent-done, say when it should finish, give a clear way to interrupt, and use a generic spinner only as a last resort. If the total work is unknown, show running progress (https://www.nngroup.com/articles/response-times-3-important-limits/).
- For 10 s or more, use a percent-done indicator. Avoid a static "Loading...". Give an estimate rounded up. The bar should start slow and speed up, never shoot up and stall. If the estimate is long, let the user leave (a notice or a callback). Users with a progress bar waited about 3x longer (https://www.nngroup.com/articles/progress-indicators/).
- Application: the cold start has no measurable real progress, so the bar would be faked. An honest alternative is to show real stages (waking the server, loading the model, ready) and the elapsed time, with the explanation of why it takes long. This is my inference from NN/g (running progress when the total is unknown).

## 4. Chat accessibility (WCAG 2.2 AA)

- `role="log"` has implicit `aria-live="polite"` and `aria-atomic="false"`, requires an accessible name (`aria-label`/`aria-labelledby`) and fits chat, with new messages only at the end. MDN gives no chat-specific guidance between polite and assertive (https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/log_role). My recommendation: use `role="log"` on the message list and `role="status"` on the typing indicator and on the warm-up status.
- SC 4.1.3 (AA): status messages must be programmatically identifiable without moving focus. `role="log"` and `role="status"` are sufficient techniques for progress. Using `role="alert"` or `assertive` on non-urgent content is a common failure (https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html).
- Motion: SC 2.3.3 is level AAA, not AA. Technique C39 uses `prefers-reduced-motion` (https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html). Apply it to the typing indicator anyway (swap the pulse for a static "digitando…"). I did not confirm the 5 s threshold of SC 2.2.2 on the page I consulted.
- Contrast: SC 1.4.11 requires 3:1 for UI components and the focus indicator (https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html). The 4.5:1 for text comes from SC 1.4.3, which I did not open in this research (general knowledge). Text in bubbles must pass 4.5:1.
- Focus and keyboard: I did not consult a specific source. Suggested practice: focus stays on the input when sending, Enter sends, do not steal focus when a message arrives. Mark as unverified.

## 5. Design tokens

- The DTCG published the first stable version, **2025.10**, on 28/10/2025 (https://www.designtokens.org/). Extension and media type not confirmed.
- GSP generates `tokens.json` in the W3C Design Tokens format and by convention maps `color.brand.primary` to `--color-brand-primary` and to `text-brand-primary` in Tailwind (`~/.claude/references/design-tokens.md`, section "Token-to-Code Mapping"). The patterns SKILL asks for the `tech_stack` and, for Tailwind, extends the config (`gsp-brand-patterns/SKILL.md`). For Vite+React I suggest CSS custom properties on `:root`, since that is what GSP produces directly. Style Dictionary is cited as a conversion tool (same reference file).
- I did not confirm which version of the format GSP's `tokens.json` uses (`$value`/`$type` vs. the earlier draft).

## Recommended decisions for Phase 1

1. **Fix the GSP installation before starting.** Run `pnpm dlx get-shit-pretty --claude --global` (or `--local`), because `~/.claude/agents/` is empty. Then test with `/gsp-doctor` and `/gsp-help` to confirm the command syntax. Run the installer in a real terminal, and the questions in `/gsp:start` and strategy require the owner to be present.
2. **Lean path:** start → brand-strategy → brand-identity → brand-patterns → project-brief → project-design → project-critique. Skip brand-research and brand-audit. Shorter alternative: `/gsp:style` with a preset for tokens, if the full branding is too heavy.
3. **Honest warm-up:** real stages with elapsed time, an estimate rounded up ("normalmente 30 s a 3 min"), a direct explanation that the model runs on a GPU that needs to power on, and an option to leave and come back. No bar faking precision. `role="status"` for the text.
4. **Chat:** `role="log"` with an accessible name, typing indicator with `role="status"` and `prefers-reduced-motion`, delay between bubbles proportional to length (floor and ceiling, with jitter), parameterized in constants for calibration. The "conversar como…" selector labeled as a simulation of the WhatsApp identity.
5. **Tokens:** export `tokens.json` (DTCG) to CSS custom properties; Tailwind only if the project already uses it. Contrast targets: 4.5:1 text, 3:1 UI and focus.
