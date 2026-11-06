# Empório da Música Agent

Agente de atendimento ao cliente da loja Empório da Música (case técnico Artefact).

Em construção, ver `docs/superpowers/specs/`.

## Como rodar

Pré-requisitos: Docker, [uv](https://docs.astral.sh/uv/), Node ≥ 20 e `make`.

1. `cp .env.example .env` e `make setup`.
2. `make web-keys` gera o `SESSION_SECRET` no `.env`.
3. Defina `DEMO_EMAIL` e `DEMO_PASSWORD` no `.env`: é o login da demo, escolhido por quem roda. Nunca vai pro git.
4. Escolha o modelo: a chave do provedor no `.env` (`LLM_PROVIDER` e a `*_API_KEY` dele), ou `EMPORIO_FAKE_MODEL=1` pro modelo de teste, que não precisa de chave.

Comandos:

- `make up [PROVIDER=...]`: sobe banco, Langfuse e o frontend, e serve a demo em http://localhost:8000.
- `make dev`: API com reload em :8000 mais o Vite (que repassa `/api`), pra mexer no código.
- `make e2e`: o fluxo no navegador (Playwright) contra um servidor de verdade, com o modelo de teste; `make e2e PROVIDER=gemini` usa o modelo real.
- `make check` (backend) e `make check-web` (frontend): lint, tipos e testes.
