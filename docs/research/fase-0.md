# Pesquisa: Fase 0, fundação do repositório

As versões foram conferidas em 05/11/2026, nas páginas de release do GitHub e no PyPI.

| Ferramenta | Versão |
|---|---|
| uv | 0.13.7 |
| ruff / ruff-pre-commit | 0.17.3 |
| setup-uv | v10.3.3 |
| gitleaks | v8.30.1 |
| gitleaks-action | v3.0.0 |
| pre-commit-hooks | v6.0.0 |
| pre-commit | 4.7.0 |
| import-linter | 2.15 |
| basedpyright | 1.40.2 |
| Ollama | v0.40.14 |

## 1. AGENTS.md e CLAUDE.md
- O Claude Code lê o `AGENTS.md` só quando não existe `CLAUDE.md` (nem `CLAUDE.local.md`) no diretório atual ou acima dele. Isso vale a partir da versão v2.1.277. Fonte: https://code.claude.com/docs/en/memory#agents-md
- Um `CLAUDE.md` com uma única linha, `@AGENTS.md`, é a forma recomendada: o Claude nunca lê o arquivo duas vezes. É melhor que um symlink, que vira texto no Windows e bloqueia as ferramentas Edit/Write. Mesma fonte.
- O alvo é ficar abaixo de 200 linhas por arquivo. Imports não reduzem o custo de contexto. Regras que valem só para parte do código vão para rules com `paths`.
- A spec do agents.md não tem campos obrigatórios. Seções sugeridas: visão geral, comandos de build/test, estilo, testes, segurança e PRs. Fonte: https://agents.md

## 2. Skills e rules
- **Skills** ficam em `.claude/skills/<nome>/SKILL.md`. Só `description` é recomendado; os demais campos são opcionais (`when_to_use`, `paths`, `allowed-tools`, `disable-model-invocation`, `context: fork`…). `description` e `when_to_use` somados são truncados em 1.536 caracteres. O SKILL.md deve ter menos de 500 linhas. Fonte: https://code.claude.com/docs/en/skills
- **Rules** ficam em `.claude/rules/**/*.md`. O único campo lido é `paths`, que aceita globs. A rule carrega quando o Claude toca um arquivo que casa com o glob. Fonte: https://code.claude.com/docs/en/memory#path-specific-rules

## 3. uv
- `uv init --lib` gera `src/<pkg>/` com `py.typed`, usando o build backend `uv_build`. Fonte: https://docs.astral.sh/uv/concepts/projects/init/
- `uv add --dev` grava em `[dependency-groups].dev` (PEP 735). Fonte: https://docs.astral.sh/uv/concepts/projects/dependencies/
- No CI: `uv sync --locked` (falha se o lock estiver desatualizado), depois `uv run …`, com a versão do uv fixada. Fonte: https://docs.astral.sh/uv/guides/integration/github/

## 4. ruff e type checker
- Use `select` explícito, sem `ALL`, que liga regras novas sozinho a cada upgrade. Ponto de partida: `E, F, I, UP, B, SIM`, mais `RUF`. Fonte: https://docs.astral.sh/ruff/linter/
- Type checker: basedpyright, instalado via PyPI, sem Node, e que acompanha as releases do pyright. O `ty` ainda é pré-1.0. Fonte: https://docs.basedpyright.com/latest/

## 5. pre-commit
- Hooks na ordem: pre-commit-hooks v6.0.0 (check-yaml, check-toml, end-of-file-fixer, trailing-whitespace, detect-private-key, check-added-large-files), depois ruff-pre-commit v0.17.3 (`ruff-check --fix` antes de `ruff-format`), depois gitleaks v8.30.1.
- Fontes: https://github.com/astral-sh/ruff-pre-commit e https://github.com/gitleaks/gitleaks

## 6. import-linter 2.15
- Contratos `layers` e `forbidden`. Para proibir libs externas no domínio, é preciso `include_external_packages = true`. Só pacotes de nível raiz são aceitos: `langchain_core` precisa ser listado separado de `langchain`. A doc não confirma wildcard em `containers`, então os contextos vão listados um a um.
- Fontes: https://import-linter.readthedocs.io/en/stable/contract_types/layers/ e https://import-linter.readthedocs.io/en/stable/contract_types/forbidden/

## 7. GitHub Actions
- setup-uv v10 com cache automático, pinada por SHA. Passos: `uv sync --locked`, ruff check e format --check, basedpyright, lint-imports e pytest. Fonte: https://github.com/astral-sh/setup-uv
- gitleaks-action v3 (Node 24; a v2 deixa de funcionar em runners hospedados a partir de 16/09/2026). Não precisa de licença em conta pessoal. Use `fetch-depth: 0`. Fonte: https://github.com/gitleaks/gitleaks-action

## 8. Makefile, Compose profiles e Ollama
- **Profiles:** `profiles: [ollama]` no serviço e `docker compose --profile ollama up`. Serviços sem profile sobem sempre. Fonte: https://docs.docker.com/compose/how-tos/profiles/
- **GPU NVIDIA no Linux:** exige o NVIDIA Container Toolkit e `--gpus=all`. Fonte: https://docs.ollama.com/docker
- **macOS:** a doc diz "GPU acceleration is not available for Docker Desktop in macOS". No Mac, use o Ollama nativo (`127.0.0.1:11434`), acessado do container via `host.docker.internal` (recurso do Docker Desktop). Fonte: https://docs.ollama.com/faq
- **Tags do Gemma 4 no Ollama.** Fonte: https://ollama.com/library/gemma4/tags

  | Tag | Tamanho |
  |---|---|
  | `gemma4:e2b` | ~4,6–7,5 GB |
  | `gemma4:e4b` (`latest`) | ~6,6–9,5 GB |
  | `gemma4:12b` | ~8 GB |
  | `gemma4:26b` (MoE a4b) | ~16–19 GB |
  | `gemma4:31b` | ~19–20 GB |

## 9. Conventional Commits 1.0
- Formato: `<type>[(scope)][!]: <description>`.
- Tipos: `feat`, `fix`, `build`, `chore`, `ci`, `docs`, `style`, `refactor`, `perf`, `test`, `revert`.
- Mudança incompatível: `!` antes dos dois-pontos ou footer `BREAKING CHANGE:`.
- Fonte: https://www.conventionalcommits.org/en/v1.0.0/

## O que muda na spec por causa desta pesquisa
- **Type checker:** basedpyright, no lugar do pyright, que exige Node.
- **Contextos no import-linter:** listados explicitamente.
- **Modelo local escolhido pelo hardware** no `make up PROVIDER=local`:
  - **GPU NVIDIA ou Mac com 32 GB ou mais:** `gemma4:31b`, ou o `gemma4:26b` MoE, que é mais rápido;
  - **Mac com 16 GB** (ex.: a máquina de desenvolvimento, M4 com 16 GB): `gemma4:12b` ou `gemma4:e4b`.
  - A qualidade é medida nas evals da fase 4.
- **gitleaks no CI** via gitleaks-action v3 (o repo é de conta pessoal) e também no pre-commit.
