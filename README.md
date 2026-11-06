# Empório da Música Agent

Agente de atendimento ao cliente da loja Empório da Música (case técnico Artefact).

Em construção, ver `docs/superpowers/specs/`.

## Como rodar

Pré-requisitos: Docker, [uv](https://docs.astral.sh/uv/), Node ≥ 22.12 e `make`.

1. `cp .env.example .env` e `make setup`.
2. `make web-keys` gera o `SESSION_SECRET` no `.env`.
3. Defina `DEMO_EMAIL` e `DEMO_PASSWORD` no `.env`: é o login da demo, escolhido por quem roda. Nunca vai pro git.
4. Escolha o modelo: a chave do provedor no `.env` (`LLM_PROVIDER` e a `*_API_KEY` dele), ou `EMPORIO_FAKE_MODEL=1` pro modelo de teste, que não precisa de chave.

Comandos:

- `make up [PROVIDER=...]`: sobe banco, Langfuse e o frontend, e serve a demo em http://localhost:8000. Sem `PROVIDER`, vale o `LLM_PROVIDER` do `.env`; `PROVIDER=...` na linha de comando passa por cima dele (o mesmo vale pro `make dev`).
- `make dev`: API com reload em :8000 mais o Vite (que repassa `/api`), pra mexer no código.
- `make e2e`: o fluxo no navegador (Playwright) contra um servidor de verdade, com o modelo de teste; `make e2e PROVIDER=gemini` usa o modelo real, desde que o `.env` não tenha `EMPORIO_FAKE_MODEL`.
- `make check` (backend) e `make check-web` (frontend): lint, tipos e testes.

## Rodar o modelo na sua máquina (`PROVIDER=local`)

`make up PROVIDER=local` roda o Gemma 4 na sua máquina pelo [Ollama](https://ollama.com/download), sem chave nem custo por uso. Antes de subir, o `make local-model` escolhe o caminho e o tamanho do modelo, avisa no terminal o tamanho do download, a memória e o tempo esperado por resposta, baixa o modelo e cria o `emporio-gemma` com contexto de 16k tokens.

- **Mac com Apple Silicon:** Ollama nativo (o Docker no Mac não usa a GPU). Instale o app do Ollama antes.
- **GPU NVIDIA:** Ollama no Docker com GPU (precisa do NVIDIA Container Toolkit).
- **Só CPU:** Ollama no Docker.

**Para respostas em ~2 s, use a versão hospedada.** Rodando local, a tela de carregamento do chat avisa que cada resposta pode levar de 30 s a alguns minutos.

| Máquina | Modelo | Download | Tempo por resposta |
|---|---|---|---|
| Mac Apple Silicon, 32 GB ou mais | `gemma4:31b` | ~20 GB | 10–30 s (estimativa) |
| Mac Apple Silicon, 16 GB | `gemma4:12b` | ~8 GB | 20–60 s, menos com Metal (estimativa) |
| GPU NVIDIA com 24 GB+ de VRAM | `gemma4:31b` | ~20 GB | poucos segundos (estimativa) |
| Só CPU, 16 GB ou mais | `gemma4:12b` | ~8 GB | 20–60 s (estimativa) |
| Só CPU, menos de 16 GB | `gemma4:e4b` | ~10 GB | 10–30 s (estimativa) |

Nenhuma linha foi medida ainda; a linha medida entra aqui junto com o resultado do `make evals PROVIDER=local`.
