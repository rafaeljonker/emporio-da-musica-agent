---
paths:
  - ".env*"
  - "**/*.yml"
  - "**/*.toml"
---
- Never put real values (keys, tokens, passwords, URLs with credentials) in these files.
- Only variable names; reference them via env vars. `.env.example` has names only.
