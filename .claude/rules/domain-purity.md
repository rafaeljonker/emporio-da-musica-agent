---
paths:
  - "backend/src/emporio/*/domain/**"
  - "backend/src/emporio/shared/**"
---
- Domain code is pure: no IO, no network, no DB, no framework imports.
- Model with dataclasses and pure functions; same input, same output.
- Take time, randomness and data as arguments; never reach for globals.
- Infrastructure details belong behind ports in `application`.
