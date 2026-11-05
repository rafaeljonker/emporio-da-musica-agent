---
paths:
  - "backend/tests/**"
---
- Write the test first and watch it fail for the right reason.
- One behavior per test; name it after the behavior.
- No LLM calls in unit tests; use fakes behind the ports.
- Tests must not depend on the wall clock or on test order.
