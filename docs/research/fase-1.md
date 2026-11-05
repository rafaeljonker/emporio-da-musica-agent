# Pesquisa Fase 1: design do chat do Empório da Música

Data: 2026-11-05. Escopo: GSP, padrões de chat, esperas longas, acessibilidade, design tokens.

## 1. Get Shit Pretty (GSP)

**Instalação (README):** https://github.com/jubscodes/get-shit-pretty
- O README documenta `pnpm dlx get-shit-pretty` ou `bunx get-shit-pretty`. O `npx get-shit-pretty` aparece no SKILL local (`~/.claude/skills/get-shit-pretty/SKILL.md`), mas o README, na leitura que fiz, não o cita. Não confirmei se funciona.
- O instalador é **interativo** (pergunta runtime e global/local). Há modo não interativo: `--claude --global` ou `--claude --local` (README).
- Global grava em `~/.claude/` (skills em `~/.claude/skills/`, agents em `~/.claude/agents/`). O README não diz que o instalador cria arquivos no projeto. Os artefatos de design vão para `.design/` no projeto (`~/.claude/skills/get-shit-pretty/SKILL.md`).
- O README não define um "lean path". O mais próximo é `/gsp-style <preset>`, que gera tokens sem o branding diamond.

**Estado local (verificado):** os skills `gsp-*` existem em `~/.claude/skills/`, junto com `~/.claude/references/`, `prompts/` e `templates/`. Mas `~/.claude/agents/` está **vazio** e não há nenhum `gsp-brand-strategist*` em `~/.claude`. Os SKILLs dizem que "GSP requires a full installation to work — agents, prompts, templates" (`~/.claude/skills/get-shit-pretty/SKILL.md`). Strategy, identity, patterns, design e critique spawnam agents (`gsp-brand-strategist`, `gsp-identity-designer`, `gsp-system-architect`, `gsp-designer`, `gsp-critic`, `gsp-accessibility-auditor`; ver o `<objective>` de cada SKILL.md em `~/.claude/skills/gsp-*/SKILL.md`). Conclusão: a instalação local parece incompleta. Isso é inferência, não testei rodar um skill.

**Ordem do lean path (SKILLs locais):**
1. `/gsp:start`: cria `.design/branding/{brand}/BRIEF.md` e `.design/projects/{project}/` (`~/.claude/skills/gsp-start/SKILL.md`). Interativo (usa `AskUserQuestion`).
2. `/gsp:brand-strategy`: gera `strategy/` com 5 chunks (inclui `voice-and-tone.md`). Interativo. Lê `discover/` se existir; roda só com o BRIEF.md (`gsp-brand-strategy/SKILL.md`), então `brand-research` pode ser pulado.
3. `/gsp:brand-identity`: gera `identity/` (6 chunks + `palettes.json`). Exige a strategy completa (`gsp-brand-identity/SKILL.md`).
4. `/gsp:brand-patterns`: gera `system/` com `tokens.json`, foundations, components e `preview.html` (`gsp-brand-patterns/SKILL.md`).
5. `/gsp:project-brief`: gera `projects/{p}/brief/` (`gsp-project-brief/SKILL.md`).
6. `/gsp:project-design`: gera `projects/{p}/design/` (um chunk por tela) (`gsp-project-design/SKILL.md`).
7. `/gsp:project-critique`: roda `gsp-critic` (Nielsen) e `gsp-accessibility-auditor` (WCAG 2.2 AA) em paralelo e grava em `critique/` (`gsp-project-critique/SKILL.md`). Se houver `needs-revision`, `project-design` relê `critique/prioritized-fixes.md`.

Pré-requisito: o `brief` e o `design` leem `brand.ref` e `system/tokens.json`. Por isso o patterns não pode ser pulado, a menos que se use `/gsp:style` (`gsp-style/SKILL.md`). Observação: o README usa nomes `/gsp-...`, os SKILLs locais usam `/gsp:...`. Confirmar com `/gsp-help`.

## 2. Padrões de UI de chat

Não encontrei fonte autoritativa para bubble layout. As recomendações abaixo são convenção de mercado e minha inferência.
- Layout: bolhas do cliente à direita e do atendente à esquerda, agrupamento de mensagens consecutivas do mesmo remetente, timestamp por grupo, mobile-first com input fixo embaixo. Convenção do WhatsApp, não citável.
- **Pacing:** não há benchmark validado. Fontes do achado: vendors usam delay fixo (padrão 2 s, https://support.ingenious.ai/hc/en-au/articles/5114874768407), delay escalado ao tamanho da mensagem com mínimo e máximo (https://help.nicecxone.com/content/aiassistantsandbots/botbuilder/featuredetails/smarttyping.htm) e o módulo open source de presença WhatsApp modela 42 wpm mais jitter aleatório (https://cdn.jsdelivr.net/npm/waha-openclaw-channel@2.2.0/docs/presence.md). 42 wpm equivale a cerca de 3,5 caracteres por segundo (cálculo meu, 5 caracteres por palavra). A pesquisa recomenda delay proporcional ao tamanho, com piso e teto, e variação aleatória, tudo a ser calibrado em teste.
- A página NN/g de chatbots (`/articles/chatbots-ux-heuristics/`) retornou 404, então não há fonte NN/g sobre isso.

## 3. Esperas longas (cold start de 30 s a 3 min)

- O limite de 10 s é "o máximo que o usuário mantém a atenção". Acima disso: mostrar percent-done, dizer quando deve terminar, dar forma clara de interromper, e usar spinner genérico só como último recurso. Se o trabalho total é desconhecido, mostrar progresso corrente (https://www.nngroup.com/articles/response-times-3-important-limits/).
- Para 10 s ou mais, usar indicador percent-done. Evitar "Loading..." estático. Dar estimativa arredondada para cima. Barra deve começar lenta e acelerar, nunca disparar e travar. Se a estimativa for longa, deixar o usuário sair (aviso ou callback). Usuários com barra de progresso esperaram cerca de 3x mais (https://www.nngroup.com/articles/progress-indicators/).
- Aplicação: o cold start não tem progresso real mensurável, então a barra seria fingida. Uma alternativa honesta é mostrar etapas reais (acordando o servidor, carregando o modelo, pronto) e o tempo decorrido, com a explicação de por que demora. Isso é minha inferência a partir do NN/g (progresso corrente quando o total é desconhecido).

## 4. Acessibilidade do chat (WCAG 2.2 AA)

- `role="log"` tem `aria-live="polite"` e `aria-atomic="false"` implícitos, exige nome acessível (`aria-label`/`aria-labelledby`) e serve para chat, com novas mensagens só no fim. O MDN não dá orientação específica de chat entre polite e assertive (https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/log_role). Minha recomendação: usar `role="log"` na lista de mensagens e `role="status"` no indicador de digitação e no status do warm-up.
- SC 4.1.3 (AA): mensagens de status devem ser identificáveis por software sem mover o foco. `role="log"` e `role="status"` são técnicas suficientes para progresso. Usar `role="alert"` ou `assertive` em conteúdo não urgente é falha comum (https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html).
- Movimento: SC 2.3.3 é nível AAA, não AA. A técnica C39 usa `prefers-reduced-motion` (https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html). Aplicar mesmo assim ao typing indicator (trocar pulso por "digitando…" estático). Não confirmei o limiar de 5 s do SC 2.2.2 na página consultada.
- Contraste: SC 1.4.11 exige 3:1 para componentes de UI e focus indicator (https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html). O texto de 4.5:1 vem do SC 1.4.3, que não abri nesta pesquisa (conhecimento geral). Texto em bolhas deve passar 4.5:1.
- Foco e teclado: não consultei fonte específica. Prática sugerida: foco permanece no input ao enviar, Enter envia, não roubar foco ao chegar mensagem. Marcar como não verificado.

## 5. Design tokens

- O DTCG publicou a primeira versão estável **2025.10** em 28/10/2025 (https://www.designtokens.org/). Extensão e media type não confirmados.
- O GSP gera `tokens.json` em formato W3C Design Tokens e mapeia por convenção `color.brand.primary` para `--color-brand-primary` e para `text-brand-primary` no Tailwind (`~/.claude/references/design-tokens.md`, seção "Token-to-Code Mapping"). O SKILL de patterns pergunta o `tech_stack` e, para Tailwind, estende o config (`gsp-brand-patterns/SKILL.md`). Para Vite+React sugiro CSS custom properties em `:root`, pois é o que o GSP produz de forma direta. Style Dictionary é citado como ferramenta de conversão (mesmo arquivo de referência).
- Não confirmei a versão do formato que o `tokens.json` do GSP usa (`$value`/`$type` vs. rascunho anterior).

## Decisões recomendadas para a Fase 1

1. **Corrigir a instalação do GSP antes de começar.** Rodar `pnpm dlx get-shit-pretty --claude --global` (ou `--local`), pois `~/.claude/agents/` está vazio. Depois testar com `/gsp-doctor` e `/gsp-help` para confirmar a sintaxe de comando. Fazer o instalador rodar num terminal real, e as perguntas de `/gsp:start` e strategy exigem o Rafael presente.
2. **Caminho lean:** start → brand-strategy → brand-identity → brand-patterns → project-brief → project-design → project-critique. Pular brand-research e brand-audit. Alternativa mais curta: `/gsp:style` com um preset para tokens, caso o branding completo pese.
3. **Warm-up honesto:** etapas reais com tempo decorrido, estimativa arredondada para cima ("normalmente 30 s a 3 min"), explicação direta de que o modelo roda em GPU que precisa ligar, e opção de sair e voltar. Sem barra fingindo precisão. `role="status"` para o texto.
4. **Chat:** `role="log"` com nome acessível, typing indicator com `role="status"` e `prefers-reduced-motion`, delay entre bolhas proporcional ao tamanho (piso e teto, com jitter), parametrizado em constantes para calibrar. Seletor "conversar como…" rotulado como simulação de identidade do WhatsApp.
5. **Tokens:** exportar `tokens.json` (DTCG) para CSS custom properties; Tailwind só se o projeto já o usar. Metas de contraste: 4.5:1 texto, 3:1 UI e focus.
