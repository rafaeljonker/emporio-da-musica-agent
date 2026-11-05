# Project Brief

## Project
- **Name:** Emporio Chat
- **Type:** design (web app UI for the Empório da Música support agent demo)
- **Date:** 2026-11-05
- **Brand:** emporio-da-musica (`.design/branding/emporio-da-musica/`)

## What We're Building
- **Description:** The React web chat for the Artefact AI Engineer case: a messaging-app style conversation with the store's support agent (Python backend, LangGraph, Gemma 4 31B self-hosted on Modal). It is a demo surface for the evaluator: behind a demo login, honest about the GPU cold start, and showing the agent's human voice, tool accuracy and per-turn cost. Source: `docs/superpowers/specs/2026-11-05-emporio-agent-design.md` (sections 1, 2, 3, 5 cold start, 7.3, 7.4, 7.5, 7.14).
- **Platforms:** web, mobile-first (customers would arrive from a WhatsApp link); desktop is the evaluator's likely viewport.
- **Key screens/flows:**
  1. **Demo login.** E-mail + senha; credentials are sent outside the repo (delivery e-mail and Form). A successful login triggers GPU warm-up via `POST /warm`. Opening the page triggers nothing (no GPU spend on anonymous visits).
  2. **Warm-up.** Honest explanation: the model runs on its own GPU (Gemma 4 31B on Modal) that sleeps when idle to avoid cost. Real stages polled from `/warm/status` (ligando a GPU → carregando o modelo → pronto), elapsed time plus a rounded-up expected total, the note that with the machine always on replies take about 2 s ("normalmente 2,2 s por resposta"). A message typed during warm-up is queued and sent automatically when ready. Variants: **local without GPU** (`make up PROVIDER=local`): "o modelo está rodando na sua máquina sem GPU; cada resposta pode levar de 30 s a alguns minutos"; **provider API** (`PROVIDER=gemini|openai|anthropic`): fast path, no warm-up.
  3. **Chat.** Walnut wood-rail header with the Boca avatar; sequential agent bubbles (1–3 per reply) with typing indicator and backend-driven pacing; HandoffBubble; honest ProductCard; composer; "Conversar como…" customer selector (simulated WhatsApp caller identity from `data/customers.csv`, plus an anonymous option); optional discreet metrics panel (tokens, latency, cost in R$ per turn).
- **Out of scope:** real WhatsApp, customer login (identity comes from the channel), admin.

## Audience
- **Primary:** the Artefact evaluator, testing the agent through the hosted demo (or `make up`) and judging "lógica, clareza e iniciativa".
- **Secondary:** the brand persona Luísa (22–28, self-taught guitarist, lives on WhatsApp), whose experience the chat simulates.

## Goals
- **Business goal:** let the evaluator reach a real conversation fast and understand every wait, so the agent's voice and accuracy are what gets judged.
- **Design goal:** a chat that reads like a human store on WhatsApp (wooden counter warmth, plain text bubbles) and a warm-up that explains instead of disguising.
- **Success metrics:** WCAG 2.2 AA with no critical critique issues; zero AI tells in UI copy; login → first reply works end to end in `make e2e` (Playwright); the evaluator never faces an unexplained wait.

## Constraints
- **Platform:** web, mobile-first.
- **Tech stack:** Vite + React + TypeScript + Tailwind CSS v4 + shadcn/ui (Radix); lucide-react; Fontsource. Lives in `frontend/` of the monorepo (backend is Python in `backend/`), served by the FastAPI app on Modal as a static build.
- **Backend contract:** `/auth/login`, `/warm`, `/warm/status`, `/chat` (SSE, complete bubbles, not token streaming), `/customers`.
- **Timeline:** design in phase 1 of the project plan; build in phase 5 (Sat 07/11–Sun 08/11); case due Mon 2026-11-09.
- **Accessibility:** WCAG 2.2 AA.

## Scope
- **Design scope:** full
- **Target screens:** demo login, warm-up (GPU, local and provider variants), chat
- **Codebase type:** greenfield (`frontend/` created in phase 5)
- **Implementation target:** shadcn

## Deliverables
- [x] Design system + tokens (brand phase)
- [ ] UI/UX screens
- [ ] Implementation specs
- [ ] Design review
- [ ] Code components
- [ ] Marketing assets (out of scope)

## Notes
- UI copy in pt-BR following `strategy/voice-and-tone.md`; engineering docs in English; no emoji.
- Lean GSP: project research is skipped; brief → design → critique → build.
- The logo/avatar is a raster AI-generated concept pending vectorization (brand STYLE.md Bold Bet 2).
