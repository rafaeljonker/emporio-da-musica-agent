# 0003. One Postgres with pgvector

## Context

The system needs a conversation checkpointer, per-turn metrics, a vector index for the policy manual and, locally, a database for Langfuse. Running a separate store for each would multiply what a reviewer has to start and understand.

## Decision

Use a single Postgres with pgvector for all of it: the LangGraph checkpointer, the `turn_metrics` table, the policy index and the Langfuse database. Policy retrieval is hybrid: vector cosine plus Postgres full-text search, fused with reciprocal rank fusion (RRF), returning the top 5. Schema changes are plain SQL migrations with a small runner.

## Consequences

- One service to run locally (`docker compose`) and one managed instance in the hosted demo.
- On a 20-question retrieval eval, hybrid scored hit@1/3/5 of 0.75/0.95/1.00 against 0.65/0.80/0.90 for vector only. Because hit@1 is 0.75, the agent reads all five results.
- Plain SQL migrations stay readable but have no autogeneration.
- The `PolicyIndex` port keeps the vector store replaceable ([0001](0001-tools-vs-rag.md)).

## Alternatives

- A dedicated vector database: one more service for about 25 policy chunks.
- Vector-only retrieval: simpler, but measurably worse on exact terms.
- An ORM with a migration tool: more machinery than a handful of tables need.

Source: [design spec](../superpowers/specs/2026-11-05-emporio-agent-design.md), section 7.2.2.
