# Backend

The Python package `emporio` (uv project): four bounded contexts (`catalog`, `orders`, `policies`, `support`), each split into `domain/`, `application/` and `infrastructure/`, plus the web `api/`, the technical `platform/` and the composition roots in `entrypoints/`.

- `make check` (from the repo root): lint, types, import contracts and tests.
- Architecture rules and commands: [AGENTS.md](../AGENTS.md). Overview: [README.en.md](../README.en.md) / [README.md](../README.md).
