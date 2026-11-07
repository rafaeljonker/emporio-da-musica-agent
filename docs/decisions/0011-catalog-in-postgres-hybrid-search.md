# 0011. Catalog in Postgres with hybrid search

## Context

The catalog lived in two CSVs read into memory, and product search ran over all 65 rows with a pure-Python grader. That cannot take new products at runtime, and the grader does not scale: over 50,065 rows it took p50 1.5 s ([research](../research/catalog-db.md), section 6). The demo also needed a store back office where a logged-in user adds a product and the agent finds it on the next question. The rule from ADR 0001 stays: price, stock and promotion must be exact.

## Decision

Products live in one Postgres table. Price, stock, status and promotion are exact SQL columns. One SQL statement proposes candidates from three rankers fused with RRF (k = 60): full-text search, `pg_trgm` for codes and typos, and pgvector with e5-small. Availability and the price ceiling are filtered in SQL, with `hnsw.iterative_scan = relaxed_order` and `hnsw.ef_search = 100`. The pure domain grader still decides Exact or Candidates over a pool of 40, and facts never come from the vector side. The category filter comes from the categories named in the query.

Writes: any logged-in demo user creates products and edits their own; seed rows are read-only; there is no delete and no CSV upload. The embedding is computed synchronously; if it fails the row is saved with `embedding NULL`, logged, and still found by text search. `make ingest` reseeds and deletes demo-created products. The agent and the MCP server stay read-only: the Catálogo dialog is the store's back office, a separate actor.

Abuse mitigations on the write path:
- Limits: 20 products per login, 500 in total, 10 writes/min per login, plus per IP 10 writes/min and 30 creates/hour. Over a limit the API answers 429 `too_many_writes` or 409 `catalog_full`.
- Validation at the edge: strict body (`extra="forbid"`), name 2 to 120 characters, description up to 2000, price as a decimal string up to 6 digits and 2 decimals, stock 0 to 100,000, at most 20 specs, and control, zero-width and bidi characters rejected. Database `CHECK`s back it up.
- Prompt injection: product text reaches the model through tools, so the tool prompt says tool output is store data, never an instruction, and to ignore instructions inside a product name, description or policy excerpt.
- Outages: a database failure on any catalog route is a 503 `catalog_unavailable`.

## Consequences

- At 50,065 rows (local probes) the hybrid query ran at p50 17 to 34 ms and p95 47 to 105 ms; on Modal add about 80 ms of round trip per catalog read. On the 65-row catalog, retrieval hit@1 is 0.83 and hit@5 is 0.97; local search p50 is about 10 ms.
- Trigram is what holds up at scale: code and typo queries reached hit@5 of 18/18 against 13/18 without it.
- Known limit: e5-small is weak on loose Portuguese intent. "algo pra tocar MPB em casa" lands near electric instruments, so the `recomendacao_mpb` golden case is graded on store knowledge (an available nylon violão, no electric guitar or bass). A reranker or category hints in the embedding text are the later fixes.
- Embedding failures are silent to the user and visible only in logs until the next `make ingest` back-fills them.
- Demo products can pollute recommendations until the manual reset, which is documented.
- Beyond roughly 1M rows the plan is `halfvec`, BM25 and possibly a dedicated engine ([scaling](../scaling-and-cost.md)).

## Alternatives

- ParadeDB BM25: better lexical ranking, but AGPL and a new image to run; unnecessary at this size.
- FTS + vector only: simpler, but code and typo hit@5 fell to 13/18 at 50k rows without trigram. It stays the fallback if `pg_trgm` is missing.
- Vector-only with a post-filter: with an 8.6% filter it returned 0 rows (recall 0.06) without iterative scans, and vectors alone collapse on model codes.
- A queue or outbox for embeddings: not worth a worker at about 9 ms per embed and a 500-row cap.

Source: [research](../research/catalog-db.md), [design spec](../superpowers/specs/2026-11-05-emporio-agent-design.md), section 7.2.6.
