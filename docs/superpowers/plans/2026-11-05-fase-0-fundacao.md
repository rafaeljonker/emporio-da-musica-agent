# Fase 0: Fundação do repositório (plano de implementação)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar o repositório `emporio-da-musica-agent` com o esqueleto DDD do backend Python e as instruções para agentes. As ferramentas de qualidade (lint, tipos, camadas, segredos, testes) já rodam localmente e no CI, de modo que as fases 2 a 7 só acrescentam código.

**Architecture:** Monorepo. Nesta fase existe só `backend/`, um pacote `emporio` em src layout gerido pelo uv, com os contextos `shared`, `catalog`, `orders`, `policies` e `support`, cada um com `domain/`, `application/` e `infrastructure/` vazios. As camadas são garantidas pelo import-linter. Também entram `AGENTS.md`, `CLAUDE.md` (`@AGENTS.md`) e `.claude/rules`. Os segredos são barrados por gitleaks no pre-commit e no CI. `frontend/`, `docker-compose.yml` e `make up` entram nas fases 3 e 5.

**Tech Stack:** Python 3.12, uv, ruff 0.17.3, basedpyright, pytest, import-linter 2.15, pre-commit 4.7 (pre-commit-hooks v6.0.0, ruff-pre-commit v0.17.3, gitleaks v8.30.1), GitHub Actions (setup-uv v10, gitleaks-action v3), GNU Make.

**Spec:** `docs/superpowers/specs/2026-11-05-emporio-agent-design.md`, seções 7.7, 7.9, 7.10, 7.12, 7.13 e 7.14. **Pesquisa:** `docs/research/fase-0.md`.

## Global Constraints
- Caminho do repo: `~/Documents/projetos/my-projects/emporio-da-musica-agent`.
- Python 3.12, fixado em `backend/.python-version`. O pacote se chama `emporio` e fica em `backend/src/emporio/`.
- Código, identificadores, commits e PRs em **inglês**. README, `docs/`, ADRs e exemplos em **português** (spec 7.13).
- Conventional Commits com escopo, por exemplo `chore(repo): …` ou `ci: …`. Assunto com até 72 caracteres, no imperativo. Todo commit termina com o trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Fluxo de git: commit inicial na `main` e o resto da fase na branch `chore/foundation`. O PR é aberto e o merge só acontece depois do ok do responsável no checkpoint, com merge commit e sem squash. Nada de force-push.
- Nenhum segredo entra no git: `.env*` fica no `.gitignore`, exceto `.env.example`, que só leva nomes de variáveis.
- **Não commitar o PDF do enunciado** (`desafio_tecnico_ai_eng_artefact.pdf`), que é material do processo seletivo. Entram em `data/` só os 6 CSVs e o `políticas_da_loja.pdf`, que o agente usa.
- `AGENTS.md` com menos de 200 linhas. Rules em `.claude/rules/*.md`, só com `paths:` no frontmatter.
- Repo no GitHub **privado** até a entrega (confirmado em 05/11).

## Review Focus
1. **`.env` com chave real commitado por engano.** Esperado: o pre-commit (gitleaks) bloqueia, e o CI falha. Teste: Task 4, Step 2.
2. **Nome com espaço e acento em `data/`** (`desafio_tecnico_ai_eng - products.csv`, `políticas_da_loja.pdf`). Esperado: os arquivos existem com o nome exato e são legíveis via `pathlib`. Teste: `test_case_data_files_are_present` na Task 2.
3. **`uv.lock` desatualizado.** Esperado: `uv sync --locked` falha no CI, em vez de instalar versões diferentes. Verificação: Task 5, Step 3.
4. **Domínio importando framework**, como `langchain_core` (o pacote raiz é diferente de `langchain`). Esperado: o `lint-imports` falha. Teste: Task 3, Step 2.
5. **PDF do enunciado entrando no repo por `git add .`.** Esperado: o `.gitignore` exclui o arquivo. Verificação: Task 1, Step 2 (`git status`). Não vira teste de pytest, porque é regra do repositório e não comportamento do programa.

---

### Task 1: Repositório, documentos da fase e dados do case

**Files:**
- Create: `.gitignore`, `.env.example`, `README.md` (stub em português: uma frase + "em construção, ver `docs/superpowers/specs/`")
- Create: `docs/superpowers/specs/2026-11-05-emporio-agent-design.md`, `docs/superpowers/plans/2026-11-05-fase-0-fundacao.md` e `docs/research/fase-0.md`, criados nesta tarefa (versões aprovadas da spec, do plano e da pesquisa)
- Create: `docs/decisions/0001-tools-vs-rag.md`. ADR em português, formato contexto, decisão e consequências, sobre o princípio 7.1 da spec: dado estruturado vai para tool, texto vai para RAG.
- Create: `data/` com os 6 CSVs da quarentena (nomes originais) e `data/políticas_da_loja.pdf`, copiado de `pol_ticas_da_loja.pdf`

**Interfaces:**
- Produces: a pasta `data/`, que as fases 2 e 3 leem pelos nomes exatos acima.

- [ ] **Step 1:** `mkdir` do repo, `git init -b main`, e cópia dos docs e dos dados. O `.gitignore` cobre `.env`, `.env.*`, `!.env.example`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `node_modules/`, `.superpowers/`, `.design/cache/` e `**/desafio_tecnico_ai_eng_artefact.pdf`. O `.env.example` traz só comentários com os nomes previstos: `LLM_PROVIDER`, `VLLM_BASE_URL`, `VLLM_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DATABASE_URL`, `DEMO_USER`, `DEMO_PASSWORD`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `STORE_TODAY`.
- [ ] **Step 2:** Rodar `git status --porcelain`. Esperado: nenhum PDF do enunciado e nenhum `.env` listados.
- [ ] **Step 3: Commit na `main`**
```bash
git add -A && git commit -m "docs(repo): add design spec, phase 0 plan, research and case data"
```
- [ ] **Step 4:** `git switch -c chore/foundation`

### Task 2: Pacote `emporio` com uv e esqueleto DDD

**Files:**
- Create: `backend/pyproject.toml` via `uv init --lib --name emporio backend`, `backend/.python-version` (`3.12`), `backend/uv.lock`
- Create: `backend/src/emporio/{shared,catalog,orders,policies,support}/__init__.py`, e em cada contexto, exceto `shared`, `domain/__init__.py`, `application/__init__.py` e `infrastructure/__init__.py`, todos vazios
- Create: `backend/src/emporio/paths.py`
- Test: `backend/tests/test_paths.py`

**Interfaces:**
- Produces:
  - `emporio.paths.REPO_ROOT: Path` e `emporio.paths.DATA_DIR: Path` (`REPO_ROOT / "data"`);
  - `emporio.paths.CASE_CSV_FILES: dict[str, Path]`, com as chaves `products`, `promotions`, `customers`, `categories`, `order_items` e `orders`, que apontam para `desafio_tecnico_ai_eng - <chave>.csv`;
  - `emporio.paths.POLICIES_PDF: Path` (`DATA_DIR / "políticas_da_loja.pdf"`).
  - As fases 2 e 3 usam esses nomes.

- [ ] **Step 1: Escrever os testes que falham**
```python
from emporio import paths

def test_case_data_files_are_present():
    assert set(paths.CASE_CSV_FILES) == {"products", "promotions", "customers", "categories", "order_items", "orders"}
    for f in [*paths.CASE_CSV_FILES.values(), paths.POLICIES_PDF]:
        assert f.is_file() and f.stat().st_size > 0, f
```
A estrutura de camadas não ganha teste próprio: quem garante as dependências entre camadas é o import-linter (Task 3).
- [ ] **Step 2:** `cd backend && uv add --dev pytest ruff basedpyright import-linter pre-commit`, seguido de `uv run pytest -q`. Esperado: FAIL com `ModuleNotFoundError: emporio.paths`.
- [ ] **Step 3: Implementar `emporio/paths.py` e os `__init__.py`.** `REPO_ROOT` é `Path(__file__).resolve().parents[3]`.
- [ ] **Step 4: Config em `pyproject.toml`.** O que dá para checar com ferramenta fica na ferramenta.
  - `[tool.ruff]` com `line-length = 100` e `target-version = "py312"`.
  - `[tool.ruff.lint] select = ["E","F","I","UP","B","SIM","RUF","ANN","BLE","TRY","DTZ","S","PT","RET","C4","PIE","PERF"]`.
  - `[tool.ruff.lint.per-file-ignores]`: em `"tests/**"`, ignorar `["S101","ANN201"]` (assert e retorno sem anotação são aceitos em teste).
  - `[tool.basedpyright]` com `typeCheckingMode = "standard"` e `include = ["src","tests"]`, mais `strict = ["src/emporio/*/domain", "src/emporio/*/application", "src/emporio/shared"]`. Se o glob em `strict` não for aceito, liste os caminhos de cada contexto.
  - `[tool.pytest.ini_options]` com `testpaths = ["tests"]`.
  - **Prova de que os gates mordem (red):** um arquivo temporário `src/emporio/shared/_probe.py` com `def f(x): return datetime.now()` precisa falhar em `ruff` (ANN e DTZ) e em `basedpyright` (strict). Depois, remover o arquivo.
- [ ] **Step 5:** `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run basedpyright`. Esperado: tudo verde.
- [ ] **Step 6: Commit** `chore(backend): scaffold emporio package with ddd context layout`

### Task 3: Contratos de camadas (import-linter)

**Files:**
- Modify: `backend/pyproject.toml` (seção `[tool.importlinter]`)

**Interfaces:**
- Produces: o comando `uv run lint-imports`, que todas as fases rodam. Os contratos valem para o código que elas vão criar.

- [ ] **Step 1: Escrever os contratos.**
  - `root_packages = ["emporio"]` e `include_external_packages = true`.
  - **Um contrato `layers` por contexto**, listados explicitamente porque a pesquisa não confirma wildcard em `containers`. Cada um com `containers = ["emporio.<ctx>"]` e `layers = ["infrastructure", "application", "domain"]`.
  - **Um contrato `forbidden`** com:
    - `source_modules = ["emporio.catalog.domain", "emporio.orders.domain", "emporio.policies.domain", "emporio.support.domain", "emporio.shared"]`;
    - `forbidden_modules = ["fastapi", "langchain", "langchain_core", "langgraph", "sqlalchemy", "psycopg", "duckdb", "httpx", "openai", "anthropic", "google"]`.
- [ ] **Step 2: Provar que o contrato morde (red).** Criar temporariamente `emporio/catalog/domain/_probe.py` com `import langchain_core`. Pode ser preciso instalar `langchain-core` só como dev temporário; se não estiver instalado, usar `import fastapi` após um `uv add --dev fastapi` temporário. Rodar `uv run lint-imports`. Esperado: FAIL citando `emporio.catalog.domain._probe`. Depois, remover a sonda e reverter a dependência temporária com `git checkout -- backend/pyproject.toml backend/uv.lock` antes de aplicar a config final.
- [ ] **Step 3:** `uv run lint-imports`. Esperado: `Contracts: N kept, 0 broken.`
- [ ] **Step 4: Commit** `chore(backend): enforce layer and domain-purity contracts with import-linter`

### Task 4: pre-commit com ruff e gitleaks

**Files:**
- Create: `.pre-commit-config.yaml` na raiz, com os hooks e revs exatos de `docs/research/fase-0.md` §5. Os hooks de ruff usam `args: [--config, backend/pyproject.toml]` e `files: ^backend/`.

- [ ] **Step 1:** `cd backend && uv run pre-commit install --config ../.pre-commit-config.yaml`, seguido de `uv run pre-commit run --all-files`. Esperado: Passed. Corrija o que os fixers mudarem e rode de novo.
- [ ] **Step 2: Provar que o gitleaks bloqueia (red).** Criar `leak_probe.txt` com uma chave falsa no formato AWS, montada em tempo de execução e não escrita no plano. Exemplo: `printf 'aws_secret_access_key = %s\n' "$(python3 -c "print('A'*4+'KIA'+'Q'*16)")"`; se esse formato não disparar, use outra regra padrão do gitleaks. Rodar `git add leak_probe.txt && git commit -m probe`. Esperado: o commit é bloqueado pelo hook `gitleaks`. Depois, remover o arquivo e rodar `git reset`.
- [ ] **Step 3: Commit** `chore(repo): add pre-commit with ruff and gitleaks`

### Task 5: CI no GitHub Actions

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Produces:
  - os jobs `backend-quality`, `backend-tests` e `secrets`. As fases seguintes **estendem** esse arquivo sem renomear os jobs:
    - fase 3: serviço Postgres + pgvector em `backend-tests`;
    - fase 5: jobs `frontend` e `e2e`.
  - Workflows separados e manuais, em fases futuras: `evals.yml` (fase 4), `deploy.yml` e `load.yml` (fase 6).

- [ ] **Step 1: Escrever o workflow.**
  - **Gatilhos:** `push` e `pull_request`.
  - **Topo do arquivo:** `permissions: contents: read` e `concurrency: {group: ci-${{ github.ref }}, cancel-in-progress: true}`.
  - **`backend-quality`** (`working-directory: backend`, filtro de caminho `backend/**` ou `.github/workflows/**`): `actions/checkout` e `astral-sh/setup-uv@v10`, pinado por SHA, com o SHA resolvido via `gh api repos/astral-sh/setup-uv/git/ref/tags/v10.3.3`. Depois rodam `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run basedpyright` e `uv run lint-imports`.
  - **`backend-tests`:** mesmo setup e mesmo filtro, seguido de `uv sync --locked` e `uv run pytest -q`.
  - **`secrets`:** `actions/checkout` com `fetch-depth: 0` e `gitleaks/gitleaks-action@v3`, com `GITHUB_TOKEN`. Roda sempre, sem filtro de caminho.
  - **Filtro de caminho por job:** use `dorny/paths-filter`, pinado por SHA, num job `changes` do qual os outros dependem. `on.paths` filtraria o workflow inteiro, e o `secrets` precisa rodar sempre.
- [ ] **Step 2:** Validar a sintaxe com `uvx check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/ci.yml`. Esperado: ok.
- [ ] **Step 3: Provar o `--locked` (red).** Rodar `cd backend && uv add --dev --frozen rich`, que muda o `pyproject.toml` sem atualizar o lock, e depois `uv sync --locked`. Esperado: FAIL. Reverter com `git checkout -- pyproject.toml`.
- [ ] **Step 4: Commit** `ci: add parallel backend quality, tests and secret scanning jobs`

### Task 6: AGENTS.md, CLAUDE.md, rules e Makefile

**Files:**
- Create: `AGENTS.md` (inglês, menos de 200 linhas, seções na ordem a seguir):
  - Overview, com 3 linhas e link para a spec;
  - Commands (`make check`, `make test`, `make fmt`);
  - Architecture rules: a tabela de dependências da spec 7.7 e "domain has no IO/frameworks";
  - TDD (red → green → refactor, um par de commits `test(x)` e `feat(x)`);
  - Commits & PRs: spec 7.10;
  - Secrets: "never write keys; use `.env`, see `.env.example`";
  - Language policy: spec 7.13;
  - Gotchas: os nomes dos arquivos de `data/` têm espaço e acento, então use `emporio.paths`. Code style: cite `.claude/rules/python-style.md` e diga que os gates do ruff e do basedpyright strict são lei. Não repita a lista no AGENTS.md.
- Create: `CLAUDE.md`, com a única linha `@AGENTS.md`.
- Create: `.claude/rules/domain-purity.md` (`paths: ["backend/src/emporio/*/domain/**", "backend/src/emporio/shared/**"]`): domínio puro, sem IO e com dataclasses e funções puras.
- Create: `.claude/rules/tests.md` (`paths: ["backend/tests/**"]`): teste antes, um comportamento por teste, sem LLM nos testes unitários.
- Create: `.claude/rules/secrets.md` (`paths: [".env*", "**/*.yml", "**/*.toml"]`): nunca valores reais, só nomes.
- Create: `.claude/rules/python-style.md` (`paths: ["backend/**/*.py"]`). Só convenções que **ferramenta nenhuma checa**, **uma linha cada, sem exemplos, no máximo ~15 linhas no total** (para não pesar no contexto):
  - dinheiro em `Decimal`, nunca `float`;
  - entidades de domínio como `@dataclass(frozen=True)`, nunca `dict` solto;
  - Pydantic só nas bordas (API, tools, MCP, config);
  - sem `typing.Any`, sem `cast`, e `# type: ignore` só com justificativa na mesma linha;
  - exceções de domínio próprias (`OrderNotFound`, `IdentityMismatch`) em vez de `ValueError` genérico;
  - funções com nome explícito, uma responsabilidade e sem flag booleana que mude o comportamento;
  - data e hora sempre via `emporio.shared.clock`, nunca `datetime.now()` direto;
  - `logging` em vez de `print`.
  - A regra termina com: "o que o ruff/basedpyright já barram não é repetido aqui; rode `make check`".
- Create: `Makefile` com os alvos `.PHONY`:
  - `setup` (`cd backend && uv sync && uv run pre-commit install --config ../.pre-commit-config.yaml`);
  - `fmt`;
  - `lint`;
  - `typecheck`;
  - `imports`;
  - `test`;
  - `check`, que roda lint, typecheck, imports e test.
  - **Sem `up` nesta fase:** ele entra nas fases 3 e 5, por YAGNI.
- As skills `adding-agent-tool`, `writing-store-voice` e `running-evals` ficam para a fase 4, quando os fluxos que elas descrevem existirem.

- [ ] **Step 1:** `wc -l AGENTS.md`. Esperado: menos de 200. `cat CLAUDE.md`. Esperado: exatamente `@AGENTS.md`.
- [ ] **Step 2:** `make check`. Esperado: tudo verde. `make -n up`. Esperado: erro "No rule to make target", confirmando que o alvo ainda não existe.
- [ ] **Step 3: Commit** `docs(agents): add AGENTS.md, CLAUDE.md import, path rules and Makefile`

### Task 7: Repositório privado no GitHub e CI verde

- [ ] **Step 1:** `gh repo create <owner>/emporio-da-musica-agent --private --source . --remote origin`, seguido de `git push -u origin main chore/foundation`.
- [ ] **Step 2:** `gh pr create --base main --head chore/foundation`, com título `chore: phase 0 foundation`. O corpo, em inglês, resume as tasks e termina com `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 3:** `gh pr checks --watch`. Esperado: `backend-quality`, `backend-tests` e `secrets` passam.

### Task 8: Checkpoint de aprovação (sem merge antes do ok)
- [ ] **Step 1:** Mostrar o link do PR e a árvore do repo (`tree -L 4 -I '.venv|__pycache__'`), além da saída de `make check` e dos três "reds" provados nas Tasks 3, 4 e 5.
- [ ] **Step 2:** Perguntar o que muda para a fase 1 (Design/GSP). Com o ok, rodar `gh pr merge --merge` (merge commit) e partir para a pesquisa da Fase 1.
