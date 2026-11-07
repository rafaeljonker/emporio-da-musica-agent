# 0001. Structured data via tools, policy text via RAG

## Context

The store has structured data (price, stock, orders, promotions; originally CSVs, the catalog moved to Postgres in [0011](0011-catalog-in-postgres-hybrid-search.md)) and a free-text policy manual (PDF, about 20 sections). The policy itself says: "nunca fornecer informações sobre preços, estoque ou prazos sem consultar o sistema" (never provide information about prices, stock or lead times without checking the system). Exact lookups cannot be approximate semantic search.

## Decision

Structured data is answered by deterministic tools that query the structured data (exact SQL columns for the catalog, CSVs for orders). Only the policy manual goes through RAG (pgvector).

## Consequences

- The tools are typed and tested.
- The scope of the RAG stays small.
- The `PolicyIndex` port allows swapping the vector store in the future.
