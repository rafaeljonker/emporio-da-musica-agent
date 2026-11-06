# Empório da Música: agente de atendimento

Um assistente de atendimento para a loja de instrumentos Empório da Música: responde no tom de um vendedor que entende de música, consulta catálogo, promoções e pedidos em ferramentas determinísticas e busca as regras da loja no manual de políticas. Tudo em Python, num chat web que simula o WhatsApp.

**Demo:** https://emporio.fastmind.site (as credenciais foram enviadas por e-mail, fora do repositório).
**Conversas reais da demo:** [catálogo e preço](examples/01-catalogo-e-preco.md), [promoção e parcelamento](examples/02-promocao-e-parcelamento.md), [arrependimento de cliente identificada](examples/03-arrependimento-cliente-identificado.md), [pedido anônimo com verificação](examples/04-pedido-anonimo-com-verificacao.md), [acessório e fora de escopo](examples/05-acessorio-e-fora-de-escopo.md).

<img src="docs/img/conversa.png" alt="Conversa na demo: o assistente responde em balões curtos, como no WhatsApp" width="420">

Stack: LangGraph + FastAPI, Postgres com pgvector, React, Langfuse; modelo Gemini 3.8 Flash na demo, Gemma 4 31B no Modal a uma flag de distância.

## Como rodar

Pré-requisitos: Docker, [uv](https://docs.astral.sh/uv/), Node ≥ 22.12 e `make`. O Langfuse local pede cerca de 2,3 GB de RAM. Na primeira vez, o `make up` baixa o modelo de embeddings (~470 MB) e as imagens do Langfuse (~7 min).

```bash
cp .env.example .env
make setup        # dependências e hooks de pre-commit
make web-keys     # gera o SESSION_SECRET no .env
```

No `.env`, defina `DEMO_EMAIL` e `DEMO_PASSWORD`: é o login da sua demo local, escolhido por você. As chaves do Langfuse local são geradas sozinhas.

**O caminho mais curto, sem chave nenhuma:** o modelo de teste (roteirizado) sobe o sistema inteiro.

```bash
EMPORIO_FAKE_MODEL=1 make up      # abra http://localhost:8000
```

**Com um modelo de verdade:** ponha no `.env` a chave do provedor (`GEMINI_API_KEY`, `OPENAI_API_KEY` ou `ANTHROPIC_API_KEY`) e escolha o provedor na linha de comando ou em `LLM_PROVIDER`. Se a chave faltar, o `make up` falha em segundos, antes de subir o Docker.

```bash
make up PROVIDER=gemini           # ou openai, anthropic; gemma pede VLLM_BASE_URL e VLLM_API_KEY
```

**Com o modelo na sua máquina:** `make up PROVIDER=local` roda o Gemma 4 pelo [Ollama](https://ollama.com/download). Antes de subir, ele detecta a máquina (Ollama nativo no Mac com Apple Silicon, Docker com GPU NVIDIA, Docker só CPU), escolhe o tamanho do modelo pela memória, avisa o tamanho do download e o tempo esperado, e cria o `emporio-gemma` com contexto de 16k tokens. No Mac, instale o app do Ollama antes.

| Máquina | Modelo | Download | Tempo por resposta |
|---|---|---|---|
| Mac Apple Silicon, 32 GB ou mais | `gemma4:31b` | ~20 GB | 10–30 s (estimativa) |
| Mac Apple Silicon, 16 GB | `gemma4:12b` | ~8 GB | 20–60 s (estimativa) |
| GPU NVIDIA com 24 GB+ de VRAM | `gemma4:31b` | ~20 GB | poucos segundos (estimativa) |
| Só CPU, 16 GB ou mais | `gemma4:12b` | ~8 GB | 20–60 s (estimativa) |
| Só CPU, menos de 16 GB | `gemma4:e4b` | ~10 GB | 10–30 s (estimativa) |

Nenhuma linha dessa tabela foi medida ainda. Para respostas em poucos segundos, use a demo hospedada.

Outros comandos úteis:

| Comando | O que faz |
|---|---|
| `make dev` | API com reload em :8000 mais o Vite, pra mexer no código |
| `make chat ARGS="--as-customer 14 --provider gemini"` | o agente no terminal, como a cliente 14 |
| `make mcp` | as ferramentas da loja num servidor MCP (stdio), sem chave de modelo |
| `make check` / `make check-web` | lint, tipos, contratos de import e testes (backend / frontend) |
| `make e2e` | o fluxo no navegador (Playwright) contra um servidor real, com o modelo de teste |
| `make evals PROVIDER=gemini` | os 22 casos de ouro contra o modelo real; gera `backend/evals/reports/<provedor>.md` |

## Arquitetura

O princípio central: **dado estruturado vai por ferramenta determinística; texto vai por RAG.** Preço, estoque, pedido e promoção são consultas exatas em Python sobre os CSVs (o próprio manual pede "nunca fornecer preços, estoque ou prazos sem consultar o sistema"); só o manual de políticas passa por busca semântica.

```mermaid
flowchart LR
    U["Chat web (React)"] -->|"POST /api/chat, SSE"| CF["Cloudflare Worker (só na demo)"]
    CF --> API["FastAPI"]
    API --> guard["guard: loja, acessório, fora de escopo, abuso"]
    guard --> agent["agente"]
    agent <--> tools["10 ferramentas"]
    agent --> LLM["Gemini 3.8 Flash (demo) · Gemma 4 31B vLLM no Modal · OpenAI/Anthropic/Ollama por flag"]
    tools --> CSV[("CSVs: catálogo e pedidos, em memória")]
    tools --> PG[("Postgres + pgvector: políticas, histórico, métricas")]
    MCP["servidor MCP"] --> tools
    API -.-> LF["Langfuse"]
```

Cada mensagem passa primeiro por um classificador de escopo (o guard) e depois pelo agente, que chama as ferramentas quantas vezes precisar (até 5 voltas). O histórico fica num checkpointer do LangGraph no Postgres. As mesmas dez ferramentas são expostas por MCP, para qualquer outro cliente (Claude Desktop, outro agente).

## Domínios e organização

O backend (`backend/src/emporio/`) tem quatro domínios:

- **catalog:** produtos, estoque, promoções, preço final, PIX e parcelamento.
- **orders:** status, rastreio, verificação de identidade e elegibilidade de troca e devolução.
- **policies:** o manual da loja, dividido por seção, e a busca híbrida sobre ele; horário de funcionamento.
- **support:** o agente em si: persona, guard, grafo, memória, ferramentas e voz.

Cada domínio tem `domain/` (regras puras, sem IO nem framework), `application/` (um caso de uso por arquivo) e `infrastructure/` (CSV, Postgres, provedores de modelo, MCP). O `import-linter` impõe a regra de dependência em todo `make check`:

| Camada | Pode importar |
|---|---|
| `*/domain` | só `shared` e a stdlib |
| `*/application` | o próprio `domain`, outros `application` via portas, `shared` |
| `*/infrastructure` | `application`, `domain` e libs externas |
| `api/` | `support.application`, `support.domain`, `shared`, `config`; nunca infraestrutura |

## Decisões técnicas

| Decisão | Escolha | Por quê | ADR |
|---|---|---|---|
| Dados × políticas | ferramentas para dados, RAG para o manual | preço e prazo não podem ser aproximados | [0001](docs/decisions/0001-tools-vs-rag.md) |
| Framework | LangGraph: guard → agente ⇄ ferramentas | escopo e abuso testáveis fora do prompt | [0007](docs/decisions/0007-langgraph-guard-agent.md) |
| Modelo | Gemma 4 31B no Modal (vLLM, H100 FP8) | a voz mais humana do teste de modelos | [0002](docs/decisions/0002-gemma-no-modal.md) |
| Modelo da demo | Gemini 3.8 Flash | sem cold start de GPU e sem queimar o crédito | [0008](docs/decisions/0008-gemini-hosted-default.md) |
| Provedores | um factory, escolha por flag, sem fallback silencioso | trocar de modelo sem mexer no código | [0006](docs/decisions/0006-provedores-por-flag.md) |
| Recuperação e persistência | um Postgres com pgvector; busca híbrida (vetor + full-text) | um banco só para histórico, métricas e índice | [0003](docs/decisions/0003-postgres-pgvector.md) |
| Embeddings | `multilingual-e5-small` em CPU, embutido na imagem | sem segundo provedor nem chave extra | [0004](docs/decisions/0004-embeddings-locais.md) |
| Interface | chat web que simula o WhatsApp | o avaliador testa em minutos, sem conta de WhatsApp | [0005](docs/decisions/0005-canal-simulado.md) |
| Observabilidade | Langfuse obrigatório, com nomes mascarados | trace de toda resposta, sem vazar cliente | [0009](docs/decisions/0009-langfuse-mandatory.md) |
| Argumentos das ferramentas | schemas Pydantic estritos | argumento errado vira erro recuperável, não preço errado | [0010](docs/decisions/0010-strict-tool-schemas.md) |
| Prompt | persona, voz, regras de ferramenta e guard em pt-BR | regras explícitas de ferramenta pesaram mais que o tamanho do modelo | [prompts](backend/src/emporio/support/infrastructure/agent/prompts/) |

## Como escolhi o modelo

Comparei 9 modelos em 14 cenários do case, com as ferramentas reais: ferramenta certa, fato certo, marcas de IA no texto e naturalidade. Na primeira rodada, Gemini 3.8 Flash e Mistral Large 4 acertaram 14/14; o Gemma 4 31B acertou só 10/14, mas teve a voz mais humana (4,8 de 5). Com regras explícitas de ferramenta no prompt (v2) e busca tolerante a plural e acento, o Gemma chegou a 14/14 em ferramenta e 14/14 efetivo (as duas falhas restantes eram falsos negativos do verificador). Detalhes e tabelas em [docs/model-selection.md](docs/model-selection.md).

## Voz humana

A voz é escrita nos prompts ([voice.md](backend/src/emporio/support/infrastructure/agent/prompts/voice.md) e [persona.md](backend/src/emporio/support/infrastructure/agent/prompts/persona.md)): mensagens curtas, uma pergunta por vez e sempre no fim, sem markdown, sem travessão, sem frase pronta de SAC, o primeiro nome do cliente uma vez. A persona é "assistente da Empório", sem nome humano inventado.

A resposta vira até 3 balões, separados por linha em branco. O turno inteiro roda primeiro e os balões chegam com um atraso calculado no servidor (o primeiro na hora, os seguintes entre 0,7 e 2,4 s conforme o tamanho, no máximo 3 s somados), com "digitando…" na tela. O ponto final de cada balão cai, como numa mensagem de chat.

E a voz é medida, não só prometida: [`ai_tells.py`](backend/src/emporio/support/domain/ai_tells.py) marca travessão, markdown, frases banidas, emoji, excesso de exclamação, mais de uma pergunta, pergunta fora do fim, mais de 3 balões e balão longo. Os evals exigem zero marcas.

## Tratamento de dados e armadilhas

A busca de produtos normaliza acento, caixa e plural e tolera erro de digitação com `difflib` ("violuao" acha o violão), separando resultado exato de candidatos: na dúvida, o agente pergunta. Cada armadilha encontrada nos dados virou teste:

| Armadilha | Teste |
|---|---|
| produtos descontinuados, "em breve" e sem estoque não aparecem como disponíveis | `test_discontinued_and_coming_soon_are_unavailable`, `test_unavailable_products_hidden_by_default` |
| só 4 das 25 promoções estão ativas | `test_four_active_promotions` |
| o PIX de 5% não se soma à promoção | `test_pix_price_is_absent_when_promotion_active` |
| "Takamine" sozinho é ambíguo (4 produtos) | `test_takamine_returns_four_candidates` |
| pedido cancelado não pode ser devolvido | `test_cancelled_order_17_is_not_eligible` |
| e-mail de outro cliente não revela o pedido | `test_order_5_with_other_customers_email_is_rejected` |
| erro de digitação no nome do produto | `test_typo_violuao_finds_c40` |

Os testes de dados ficam em `backend/tests/integration/test_catalog_data.py` e `test_orders_data.py`; as regras puras, em `backend/tests/unit/`.

## Premissas

- **Data de referência (`STORE_TODAY`, padrão 20/02/2026):** os pedidos vão de 10/2025 a 03/2026; com a data real, nenhum estaria no prazo de devolução. Essa data deixa pedidos dentro e fora do prazo (o pedido 7 pode ser devolvido por arrependimento, o 5 não). O horário "aberto agora" usa o relógio real de Campo Grande.
- **Parcelamento:** o manual traz parcela mínima de R$ 100 numa tabela e faixas na seção 3.1; vale a 3.1 (R$ 50 de 2 a 3x, R$ 80 de 4 a 6x, R$ 100 de 7 a 12x).
- **Contato:** a capa e a seção 1.2 dão o WhatsApp (67) 3341-4444, e a seção 7 dá (67) 3321-4500; um trecho grafa o e-mail com acento. O agente usa sempre (67) 3341-4444 e contato@emporiodamusica.com.br.
- **Identidade:** quem é o cliente vem do canal (o seletor "conversar como…" na web, `--as-customer` no terminal), nunca de um argumento do modelo. Anônimo só vê um pedido se número e e-mail ou telefone conferirem.
- **"Venda final":** o manual exclui da troca itens de liquidação com aviso de "venda final", mas os dados não marcam nenhuma promoção assim; o sistema não trata compra em promoção como venda final.
- **Feriados:** lista fixa de 2025–2026; o feriado municipal de Campo Grande em 26/08 não foi confirmado.

## Qualidade

- **Testes:** 698 testes determinísticos, sem modelo, escritos antes do código (cada comportamento é um par de commits `test(...) (red)` → `feat(...)` no histórico). `make check` roda ruff, basedpyright, import-linter e pytest.
- **CI** (GitHub Actions): qualidade do backend, testes do backend (com Postgres), frontend e varredura de segredos com gitleaks.
- **Evals:** 22 casos de ouro rodando o grafo real (ferramenta esperada, fato esperado e detector de voz); meta de 90% de acerto e zero marcas de IA. Cada relatório traz as transcrições completas para auditoria.

| Provedor | Acerto | Marcas de IA | Latência p50 / p95 | Observação |
|---|---|---|---|---|
| Gemini 3.8 Flash ([relatório](backend/evals/reports/gemini.md)) | 20/22 | 0 | 5,9 s / 14,5 s | rodada final, no código entregue |
| Gemma 4 31B, H100 FP8 ([relatório](backend/evals/reports/gemma-h100-fp8.md)) | 21/22 | 4 | 2,1 s / 4,1 s | anterior às correções de voz |
| Gemma 4 31B, L40S FP8 ([relatório](backend/evals/reports/gemma-l40s-fp8.md)) | 21/22 (22/22 efetivo) | 0 | 4,9 s / 10,0 s | anterior à versão final do verificador |

As duas falhas do Gemini: uma recomendação de MPB com violões fora da lista esperada (falha real) e uma devolução fora do prazo que a resposta explica certo, mas com uma frase que o verificador por regex não reconheceu. As rodadas do Gemma não foram refeitas depois das correções de voz (balões, uma pergunta por vez, remoção da marcação de raciocínio).

## Escala e custo

O detalhe está em [docs/scaling-and-cost.md](docs/scaling-and-cost.md). Os números principais:

- **GPU:** H100 FP8 é o padrão do Gemma; a L40S custa metade por hora, mas é mais lenta e sai mais cara por resposta.
- **Cold start:** a meta era 30 s e **não foi atingida**; o melhor boot da H100 levou cerca de 204 s. Por isso a demo roda Gemini, e o login já acorda o modelo.
- **Carga** (modelo de teste, um contêiner, mede a nossa infraestrutura): 120 usuários por 2 minutos, 1.334 conversas, 0 falhas, 11,2 conversas/s, p50 de 4,2 s. O gargalo encontrado foi um lock do checkpointer que serializava todo o I/O; sem ele, o p50 com 50 usuários caiu de 48 s para 1,7 s.
- **Custo:** R$ 0,031 por caso de eval no Gemini (preço de tabela), cerca de R$ 0,12 por conversa de 4 turnos (estimativa). Projeção mensal no Gemini: ~$23 com 1k conversas, ~$225 com 10k, ~$2.255 com 100k. Uma H100 ligada no horário da loja custa ~$837/mês; o ponto de equilíbrio fica em torno de 37k conversas/mês.

## Limitações e o que eu faria com mais tempo

- **Latência do Gemini:** p50 de 5,9 s, acima da meta de 3 s (o guard é uma segunda chamada de modelo em sequência). A H100 aquecida atende a meta.
- **Cold start do Gemma:** ~3,5 min contra a meta de 30 s. Próximos passos: snapshot de memória da GPU, cache da compilação JIT do FlashInfer (~100 s por boot) ou um contêiner sempre ligado no horário da loja.
- **Evals do Gemma** não foram refeitos depois das correções de voz e marcação; o teste de carga com modelo real e o baseline BF16 ficaram de fora pelo orçamento de GPU.
- **Estado por processo:** rate limit, lock por conversa e status do aquecimento vivem em memória, então a API roda num contêiner só. Escalar pede mover isso para Postgres ou Redis e aproximar o banco da região do Modal.
- **`PROVIDER=local`** está pronto, mas os tempos da tabela não foram medidos.
- **Pendências pequenas:** a troca de cliente que falha não avisa na tela; recarregar a página apaga os balões, mas não a conversa no servidor.
- **Com mais tempo:** WhatsApp oficial como novo adaptador do canal, passagem para atendente humano, reranking na busca de políticas, cartões de produto nos balões e guardrails de dados pessoais além do mascaramento de nomes.

## Uso de assistentes de IA

O projeto foi feito com o Claude Code, num fluxo com etapas fixas. Primeiro uma conversa de brainstorming virou a [spec](docs/superpowers/specs/2026-11-05-emporio-agent-design.md). Cada fase começou com pesquisa na documentação atual das libs (em `docs/research/`), seguida de um plano curto. A implementação foi em TDD com subagentes: um teste falhando, depois o código que o faz passar, e o par fica visível no histórico de commits. Cada fase passou por uma revisão independente feita por lentes de risco (contratos, dados do cliente, voz, segredos, custo e escala), com uma segunda rodada tentando derrubar cada achado ([`.claude/skills/reviewing-changes/`](.claude/skills/reviewing-changes/SKILL.md)). Nenhuma fase começou sem o ok do dono do projeto.

O contexto do assistente está versionado: [AGENTS.md](AGENTS.md) (comandos, regras de arquitetura, armadilhas; o `CLAUDE.md` só o importa), as regras em [`.claude/rules/`](.claude/rules/) (pureza do domínio, estilo Python, testes, segredos) e as skills em `.claude/skills/` (a revisão e as de design usadas na fase de interface). Commits feitos com o assistente levam o trailer `Co-Authored-By`.

O que foi decisão do dono, e não do assistente: busca híbrida nas políticas; guard em todo turno; Langfuse obrigatório; balões enviados depois do turno, sem streaming de tokens; medir H100 e L40S em FP8 e ficar com a H100; os cortes de orçamento (sem baseline BF16, sem snapshot de GPU, sem teste de carga com modelo real); Gemini na demo hospedada; e nada de LLM-como-juiz nos evals, com os fatos checados por um verificador determinístico e as transcrições nos relatórios. O assistente escreveu o código, os testes, a pesquisa e os rascunhos dos documentos; o dono escolheu entre as opções, revisou e aprovou cada fase.

## Onde encontrar cada item do enunciado

| Pedido | Onde |
|---|---|
| Projeto em Python | `backend/` (agente, ferramentas, API, evals); TypeScript só no React |
| Persona alinhada à loja | [Voz humana](#voz-humana), [prompts](backend/src/emporio/support/infrastructure/agent/prompts/) |
| Responder com base no contexto e no histórico | [Arquitetura](#arquitetura) |
| Saber quando consultar dados × políticas | [Arquitetura](#arquitetura), [ADR 0001](docs/decisions/0001-tools-vs-rag.md) |
| Lidar com fora de escopo | guard ([ADR 0007](docs/decisions/0007-langgraph-guard-agent.md)), [exemplo 5](examples/05-acessorio-e-fora-de-escopo.md) |
| Decisões justificadas (framework, LLM, recuperação, prompt, interface, persistência, dados) | [Decisões técnicas](#decisões-técnicas), [Tratamento de dados](#tratamento-de-dados-e-armadilhas) |
| Como rodar | [Como rodar](#como-rodar) |
| Limitações e o que faria com mais tempo | [Limitações](#limitações-e-o-que-eu-faria-com-mais-tempo) |
| Uso de assistentes de IA | [Uso de assistentes de IA](#uso-de-assistentes-de-ia) |
| 3 a 5 conversas de exemplo | [`examples/`](examples/) |
| Ambiguidades assumidas e documentadas | [Premissas](#premissas) |
