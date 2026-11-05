# AGENTS.md

## Overview
Emporio da Musica Agent: a customer-support chat agent for a music store (catalog, orders, store policies), built in Python.
Backend lives in `backend/` (uv project, package `emporio`); the agent answers in Brazilian Portuguese.
Full design: [docs/superpowers/specs/2026-11-05-emporio-agent-design.md](docs/superpowers/specs/2026-11-05-emporio-agent-design.md).

## Commands
Run from the repo root; all targets execute in `backend/`.
- `make setup`: install deps and pre-commit hooks.
- `make check`: lint + typecheck + import contracts + tests. Must be green before every commit.
- `make test`: pytest only.
- `make fmt`: ruff format and `ruff check --fix`.

## Architecture rules
Enforced by `import-linter` (`make imports`).

| Layer | May import |
|---|---|
| `*/domain` | only `shared` and stdlib. No LangChain, SQL, FastAPI or IO |
| `*/application` | own `domain`, other `application` via ports, `shared` |
| `*/infrastructure` | `application`, `domain` and external libs |
| `api/`, `cli.py` | `support.application` and `config` (never another domain's `infrastructure`, only via the factory) |

Domain has no IO and no frameworks. One use case per file.

## TDD
Red, green, refactor. Each behavior is a pair of commits: `test(x): <behavior> (red)` then `feat(x): <behavior>`, optionally `refactor(x)`.

## Commits & PRs
- Conventional Commits with the domain as scope: `feat(catalog): ...`, `docs(readme): ...`, `chore(repo): ...`, `ci: ...`.
- Subject at most 72 chars, imperative; body explains the why when not obvious.
- AI-assisted commits carry the `Co-Authored-By` trailer.
- One branch per milestone (`feat/catalog`, `feat/agent`, ...); PR with a short description; merge commit, no squash.
- Never force-push. Never rewrite `main`.

## Secrets
Never write keys or real values in any file. Use `.env` (git-ignored); `.env.example` lists names only.

## Language policy
- English: code, identifiers, commit messages, PRs, this file.
- Portuguese: README, `docs/`, ADRs, `examples/`.
- The agent talks to customers in Brazilian Portuguese.

## Gotchas
- Files in `data/` have spaces and accents in their names; never hardcode them, use `emporio.paths`.
- `data/` is read-only source material.

## Code style
Conventions no tool checks are in `.claude/rules/python-style.md`. The ruff and basedpyright (strict) gates are law: fix the code, do not silence them.
