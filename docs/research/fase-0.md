# Research: Phase 0, repository foundation

Versions were checked on 05/11/2026, on the GitHub release pages and on PyPI.

| Tool | Version |
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

## 1. AGENTS.md and CLAUDE.md
- Claude Code reads `AGENTS.md` only when there is no `CLAUDE.md` (nor `CLAUDE.local.md`) in the current directory or above it. This holds from version v2.1.277. Source: https://code.claude.com/docs/en/memory#agents-md
- A `CLAUDE.md` with a single line, `@AGENTS.md`, is the recommended form: Claude never reads the file twice. It is better than a symlink, which turns into plain text on Windows and blocks the Edit/Write tools. Same source.
- The target is to stay under 200 lines per file. Imports do not reduce the context cost. Rules that apply only to part of the code go into rules with `paths`.
- The agents.md spec has no required fields. Suggested sections: overview, build/test commands, style, testing, security and PRs. Source: https://agents.md

## 2. Skills and rules
- **Skills** live in `.claude/skills/<name>/SKILL.md`. Only `description` is recommended; the other fields are optional (`when_to_use`, `paths`, `allowed-tools`, `disable-model-invocation`, `context: fork`…). `description` and `when_to_use` combined are truncated at 1,536 characters. SKILL.md should be under 500 lines. Source: https://code.claude.com/docs/en/skills
- **Rules** live in `.claude/rules/**/*.md`. The only field read is `paths`, which accepts globs. The rule loads when Claude touches a file that matches the glob. Source: https://code.claude.com/docs/en/memory#path-specific-rules

## 3. uv
- `uv init --lib` generates `src/<pkg>/` with `py.typed`, using the `uv_build` build backend. Source: https://docs.astral.sh/uv/concepts/projects/init/
- `uv add --dev` writes to `[dependency-groups].dev` (PEP 735). Source: https://docs.astral.sh/uv/concepts/projects/dependencies/
- In CI: `uv sync --locked` (fails if the lock is outdated), then `uv run …`, with the uv version pinned. Source: https://docs.astral.sh/uv/guides/integration/github/

## 4. ruff and type checker
- Use an explicit `select`, not `ALL`, which turns on new rules by itself on every upgrade. Starting point: `E, F, I, UP, B, SIM`, plus `RUF`. Source: https://docs.astral.sh/ruff/linter/
- Type checker: basedpyright, installed via PyPI, no Node, and it follows the pyright releases. `ty` is still pre-1.0. Source: https://docs.basedpyright.com/latest/

## 5. pre-commit
- Hooks in order: pre-commit-hooks v6.0.0 (check-yaml, check-toml, end-of-file-fixer, trailing-whitespace, detect-private-key, check-added-large-files), then ruff-pre-commit v0.17.3 (`ruff-check --fix` before `ruff-format`), then gitleaks v8.30.1.
- Sources: https://github.com/astral-sh/ruff-pre-commit and https://github.com/gitleaks/gitleaks

## 6. import-linter 2.15
- `layers` and `forbidden` contracts. To forbid external libs in the domain, `include_external_packages = true` is required. Only root-level packages are accepted: `langchain_core` must be listed separately from `langchain`. The docs do not confirm a wildcard in `containers`, so the contexts are listed one by one.
- Sources: https://import-linter.readthedocs.io/en/stable/contract_types/layers/ and https://import-linter.readthedocs.io/en/stable/contract_types/forbidden/

## 7. GitHub Actions
- setup-uv v10 with automatic cache, pinned by SHA. Steps: `uv sync --locked`, ruff check and format --check, basedpyright, lint-imports and pytest. Source: https://github.com/astral-sh/setup-uv
- gitleaks-action v3 (Node 24; v2 stops working on hosted runners from 16/09/2026). It does not need a license on a personal account. Use `fetch-depth: 0`. Source: https://github.com/gitleaks/gitleaks-action

## 8. Makefile, Compose profiles and Ollama
- **Profiles:** `profiles: [ollama]` on the service and `docker compose --profile ollama up`. Services without a profile always start. Source: https://docs.docker.com/compose/how-tos/profiles/
- **NVIDIA GPU on Linux:** requires the NVIDIA Container Toolkit and `--gpus=all`. Source: https://docs.ollama.com/docker
- **macOS:** the docs say "GPU acceleration is not available for Docker Desktop in macOS". On a Mac, use native Ollama (`127.0.0.1:11434`), reached from the container via `host.docker.internal` (a Docker Desktop feature). Source: https://docs.ollama.com/faq
- **Gemma 4 tags on Ollama.** Source: https://ollama.com/library/gemma4/tags

  | Tag | Size |
  |---|---|
  | `gemma4:e2b` | ~4.6–7.5 GB |
  | `gemma4:e4b` (`latest`) | ~6.6–9.5 GB |
  | `gemma4:12b` | ~8 GB |
  | `gemma4:26b` (MoE a4b) | ~16–19 GB |
  | `gemma4:31b` | ~19–20 GB |

## 9. Conventional Commits 1.0
- Format: `<type>[(scope)][!]: <description>`.
- Types: `feat`, `fix`, `build`, `chore`, `ci`, `docs`, `style`, `refactor`, `perf`, `test`, `revert`.
- Breaking change: `!` before the colon or a `BREAKING CHANGE:` footer.
- Source: https://www.conventionalcommits.org/en/v1.0.0/

## What changes in the spec because of this research
- **Type checker:** basedpyright, instead of pyright, which requires Node.
- **Contexts in import-linter:** listed explicitly.
- **Local model chosen by hardware** in `make up PROVIDER=local`:
  - **NVIDIA GPU or a Mac with 32 GB or more:** `gemma4:31b`, or the `gemma4:26b` MoE, which is faster;
  - **Mac with 16 GB** (e.g. the development machine, an M4 with 16 GB): `gemma4:12b` or `gemma4:e4b`.
  - Quality is measured in the phase 4 evals.
- **gitleaks in CI** via gitleaks-action v3 (the repo is on a personal account) and also in pre-commit.
