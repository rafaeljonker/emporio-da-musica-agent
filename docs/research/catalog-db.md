# Catalog research: products in Postgres with hybrid product search

Date: 2026-11-07. Delivery is 2026-11-09 23:59, so everything below is sized for about 4–5 hours of implementation with tests. Sources were read on 2026-11-07 unless a date is given. Probes ran on the owner's Apple Silicon Mac against the local compose Postgres (`pgvector/pgvector:0.8.7-pg17`, PostgreSQL 17.11, port 5434) in a scratch database `catalog_probe_scratch`, never the dev or `_test` data; the scripts lived in `/private/tmp/claude-501/catalog-probe/` and were not committed. Local timings have no network round trip; the hosted path adds the ~80 ms Modal → Railway RTT measured in `docs/scaling-and-cost.md` per query. Anything not verified is marked "unconfirmed".

## 0. What exists today
- `CsvCatalogRepository` loads the 65 products, 9 categories and 24 promotions once per process (`cached_property`). Every use case scans the full tuple: `GetProduct` (linear `next(...)`), `ListPromotions`, `SearchProducts` (filters the price ceiling in Python, then calls the pure `domain/search.py`), and `tools.py` (`_categories`, `_product_names` iterate every product on every call).
- `domain/search.py` is a 208-line stdlib grader (difflib, prefix and glued model codes, category typos) with 36 unit tests. It returns `Exact | Candidates | NoMatch`; the serializer caps Candidates at 8. It is precise on names and model codes but has no notion of meaning.
- `recommend_products` asks `PgProductIndex` (table `product_embeddings`, e5-small, HNSW) for 10 ids and filters availability in Python, because of the phase 3 rule "never filter in the vector SQL" (sparse HNSW results, `fase-3.md` §3).
- Policies already run the hybrid pattern we want to reuse: FTS `portuguese` over the immutable `f_unaccent`, OR-ed `plainto_tsquery` cast once (stem-once fix), RRF with k = 60 (`pg_policy_index.py`).
- Spec: §7.1 "structured data uses a deterministic tool; text uses RAG"; §3 non-goal "the agent reads and does not change orders or stock".

## 1. Market standard for product search
- **Hybrid lexical + semantic is the default, with lexical first for exact intent.**
  - Algolia NeuralSearch retrieves keyword and vector results independently and merges them; the `default` preset blends them "with keyword results taking priority", and typo tolerance applies only to the keyword list ("Text-based tie-breaking steps don't apply to vector results") (https://www.algolia.com/doc/guides/ai-relevance/neuralsearch/get-started).
  - Elasticsearch's `rrf` retriever fuses a lexical `standard` retriever and a `knn` retriever; a filter set at the RRF level applies to every child, and `rank_window_size` bounds what each child contributes (https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers/rrf-retriever; secondary: https://dev.to/akshay_gupta/hybrid-search-in-elasticsearch-combining-bm25-and-knn-with-rrf-2k3e).
  - OpenSearch's hybrid query normalises (min-max or L2) and combines (weighted arithmetic mean) lexical and neural scores in a search pipeline; it was GA in 2.10 (https://opensearch.org/docs/latest/search-plugins/search-pipelines/normalization-processor/).
  - Shopify made semantic search part of the Storefront API `search`/`predictiveSearch` (secondary: https://www.ecommercetimes.com/?p=178638; I found no Shopify engineering post with internals, unconfirmed). Vendor posts agree that SKUs, exact names and attributes are where keyword beats vectors.
- **Filters before ranking.** Every engine above applies hard filters (category, availability, price) to the candidate set, not to the final page; Elastic puts them on the retriever, Algolia on the query. A filter applied after a top-k cut loses results (the pgvector pitfall in §2).
- **Facts are not ranked text.** Vertex AI Search for commerce treats price, availability and quantity as "inventory fields" updated by a separate real-time API with a per-field update time to drop out-of-order writes; bulk import is for large catalog changes and streaming for small continuous ones (https://docs.cloud.google.com/retail/docs/inventory-updates). The same split fits us: price, stock, status and promotions are columns, never embedded.
- **Reranking** (a cross-encoder or an LLM over the top 20–50) is the usual third stage at large scale; here the agent's LLM already reads the candidates and asks when ambiguous, so a reranker is not needed at 10k–100k.
- **What changes with size:**
  - 10k–100k: one Postgres with GIN (FTS, trigram) and HNSW is enough; at 50k the hybrid query measured p50 17–34 ms locally (§6), the same order as the ~80 ms Modal → Railway round trip.
  - ~1M: HNSW build and memory start to matter (keep the index in RAM; `halfvec` halves it), bulk embedding becomes a batch job (§3), and BM25 statistics (IDF) begin to pay off over `ts_rank`.
  - 10M+ or many facets with counts and merchandising rules: a dedicated engine (Elastic/OpenSearch, Algolia, Vertex AI Search for commerce). The search port lets that swap happen in one adapter.

## 2. Postgres-native building blocks and their availability
| Piece | What it gives | Local image (pgvector 0.8.7-pg17) | Railway `postgres-ssl` (PG 18, pgvector 0.8.x) |
|---|---|---|---|
| FTS `tsvector` + `portuguese` + `unaccent` | stemmed word match, weights A–D, `ts_rank_cd` | yes (in use) | yes (migration 001 already runs there) |
| `pg_trgm` 1.6 | typo and partial-code match, GIN `gin_trgm_ops` | yes (`pg_available_extensions`) | contrib ships in the image ("Postgres's own contrib modules", https://github.com/railwayapp-templates/postgres-ssl); `pg_trgm` itself unconfirmed: run `SELECT name FROM pg_available_extensions WHERE name='pg_trgm'` |
| pgvector HNSW + iterative scans | semantic kNN that honours `WHERE` | yes | yes |
| ParadeDB `pg_search` (BM25, Tantivy) | real BM25 with IDF | no | no; needs a ParadeDB image service. AGPL-3.0 community edition (https://pgxn.org/dist/pg_search/0.21.0) |
| `pgvectorscale` (StreamingDiskANN) | disk-friendly ANN, label filters | no | no. PostgreSQL License (unconfirmed, sources disagree) (https://www.tigerdata.com/docs/reference/pgvectorscale) |

- **FTS.** `websearch_to_tsquery` "will never raise syntax errors", supports quotes, `OR` and `-` (https://www.postgresql.org/docs/18/textsearch-controls.html). It ANDs plain words, which is too strict for "violão de nylon para iniciante"; the policy index's OR-ed `plainto_tsquery` (stemmed once) is the better fit and is already proven here. Ranking functions "do not use any global information" (no IDF), so `ts_rank_cd` is a weak scorer on its own; inside RRF only its order matters. Use `setweight(name,'A')` so a name hit outranks a description hit.
- **pg_trgm.** Defaults: `similarity_threshold` 0.3 (`%`), `word_similarity_threshold` 0.6 (`<%`), `strict_word_similarity_threshold` 0.5. GIN `gin_trgm_ops` indexes `%`, `<%`, `LIKE/ILIKE` and regex, but not `<->` distance ordering (GiST only) (https://www.postgresql.org/docs/18/pgtrgm.html). So filter with `<%` on GIN, then order by `word_similarity` over the matched rows. A second trigram key with punctuation stripped (`code_key`: "takaminegd20dreadnought...") makes "gd 20", "gd-20" and "gd20" meet.
- **pgvector 0.8.7.** "If a condition matches 10% of rows, with HNSW and the default `hnsw.ef_search` of 40, only 4 rows will match on average"; since 0.8.0 `SET hnsw.iterative_scan = relaxed_order` (or `strict_order`) keeps scanning until enough rows pass the filter, capped by `hnsw.max_scan_tuples` (20,000 by default) and `hnsw.scan_mem_multiplier` (https://github.com/pgvector/pgvector, "Filtering" and "Iterative index scans"). AWS recommends `relaxed_order` for most production use and an outer re-sort because relaxed results can be slightly out of order (Shayon Sanyal, 2025-05-28, https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql). RRF only uses ranks, so a slightly reordered vector list is harmless; the `row_number() OVER (ORDER BY distance)` in the CTE re-sorts anyway. This **reverses the phase 3 rule** "never filter in the vector SQL": with iterative scans the filter belongs in SQL (§6 measures it).
- **`halfvec`** stores 2-byte floats, HNSW up to 4,000 dims (pgvector README); at 384 dims and 100k rows the full-precision index is small (§6), so not needed now.
- **RRF.** Supabase's reference `hybrid_search` uses `ts_rank_cd(websearch_to_tsquery)` and `<#>` CTEs, each limited to `least(match_count, 30) * 2`, a `FULL OUTER JOIN` and `1/(rrf_k + rank)` with `rrf_k` 50 (https://supabase.com/docs/guides/ai/hybrid-search). ParadeDB's "Hybrid Search in PostgreSQL: The Missing Manual" (James Blackwood-Sewell, 2025-10-22) explains why scores cannot be added across scales and uses RRF (https://paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual). We keep k = 60 (the original RRF paper's value and our policy index), and `UNION ALL ... GROUP BY id` instead of nested full outer joins, because three branches nest badly.
- **Pragmatic standard at 10k–100k:** FTS (`portuguese` + `unaccent`, weighted) + `pg_trgm` for typos and model codes + pgvector HNSW with iterative scans, the same filter in every branch, fused by RRF. No new extension beyond `pg_trgm`, no new service, everything in the Postgres we already run. BM25 (ParadeDB) and DiskANN (pgvectorscale) are the upgrades past ~1M rows and both need a different image.

## 3. Embedding pipeline on insert and update
- **Options:**
  - *Sync on write:* the admin request embeds the product and writes row + vector in one transaction. Simple, and the product is searchable when the request returns.
  - *Queue/outbox:* a trigger enqueues a job, a worker embeds in batches with retries. Supabase's "automatic embeddings" guide is the reference: insert/update triggers → `pgmq` → `pg_cron` every 10 s → `pg_net` → an Edge Function that calls an external API; it chooses async because an external API call is slow, rate-limited and can fail, and it optionally nulls the embedding on update so stale vectors never match (https://supabase.com/docs/guides/ai/automatic-embeddings). Timescale's pgai Vectorizer was the packaged version of this pattern; one third-party source says the repo was archived on 2026-02-26 (unconfirmed, https://pgxn.org/dist/pg_trickle/0.36.0/blog/pgvector-tooling-landscape.html).
  - *DB triggers that embed:* impossible here; the model runs in Python, not in Postgres.
- **Our case is different from the reference:** e5-small runs in-process on CPU (ONNX), no external API, no rate limit. One passage costs ~9–18 ms warm (§6). So **sync on write** for single products and small uploads; a **batch job** (`make ingest`/CLI) for bulk loads: e5-small embeds about 100 passages/s on this Mac when uncontended (59/s during the 50k load, which shared the CPU), so 50k products take 8–14 min (850 s measured), far too long for a request.
- **Re-embed only when the text changes.** Store `embedded_hash` = hash of the embedded document; a price, stock or status change never touches the vector. A row with `embedding IS NULL` (not yet embedded) still matches through FTS and trigram, so a failed embed degrades instead of hiding the product.
- **What to embed** (one document per product, the same text also feeds the FTS `B` weight): `"{name}. {category}. {description} {spec key: value; ...}"`, prefixed `passage: `; queries get `query: `. The e5 model card requires the prefixes and recommends `query:` on both sides only for symmetric tasks (https://huggingface.co/intfloat/multilingual-e5-small); product search is asymmetric. Typical documents are well under the 512-token limit.
- **Never embed price, stock, status or promotion.** They change often and would need a re-embed, and the embedding cannot represent "≤ R$ 1.000" reliably anyway. They are columns, filtered in SQL and read back as facts (§4).

## 4. Keeping the agent contract
- `search_products(query, max_price)` keeps its strict schema and returns the same JSON (`match`: `exact | candidates | none`, `products` via `product_json`, cap 8). `recommend_products(need)` keeps its schema too.
- **Retrieval moves to SQL; grading stays in the domain.** The hybrid query returns at most 20 filtered ids; the existing pure `search_products` grader then decides Exact/Candidates/NoMatch over that pool exactly as today (name containment, glued codes, category words, digit rules). The 36 domain tests stay valid untouched, and at 65 rows the behaviour should not change, because the pool contains every plausible product (to be confirmed by the golden cases, §10). A NoMatch from the grader on a meaning query ("bateria para gravar em estúdio") falls back to the fused list as Candidates, which is what `recommend_products` gives today.
- **Facts come from columns at answer time:** price, PIX, stock, status and the best active promotion are read in the same query as the product (`LEFT JOIN LATERAL` best promotion), and `quote_price`/`best_active_promotion` stay pure domain code. No fact ever comes from the vector side.
- **Availability and price ceiling become SQL filters** in every branch (`status='active' AND stock>0`; final price after the best active promotion `<= max_price`). The NoMatch → `include_unavailable=True` retry in `tools.py` stays, so discontinued items are still reported with their status.
- **Ambiguity stays Candidates.** Several close hits are returned, the agent asks; the spec's grading rules (§7.2.1) are unchanged.
- **What to measure:**
  - Retrieval quality: a labelled set `backend/evals/products_retrieval.toml`. The 30 cases used in §6 (11 model-code, 7 typo, 12 meaning, built from `data/` products) are the proposal; gate hit@5 ≥ 0.9 overall and report hit@1 per group, like the policies eval.
  - Latency: the hybrid query at 50k synthetic rows, p50/p95, with and without filters (§6), plus one RTT on Modal.
  - Regression: the 22 golden agent cases (`make evals`), in particular `catalogo_violoes`, `preco_takamine`, `takamine_ambiguo`, `descontinuado`, `recomendacao_mpb`, `promocoes`.

## 5. Admin product upload in the demo
- **It does not contradict the spec.** §3 says the *agent* does not write store data, and that holds: no tool writes, the MCP server stays read-only. The admin screen is store staff's back office, a separate actor. It needs one ruling line in the spec (§7.2.x) and one README line. `data/` stays read-only: the CSVs only seed.
- **Minimal safe design:**
  - *Who:* a separate admin credential (`ADMIN_EMAIL`/`ADMIN_PASSWORD`, same `hmac.compare_digest` login) that sets `role=admin` in the session; the demo login cannot reach `/api/admin/*`. Evaluators receive the admin credential only if the owner wants them to try it.
  - *What:* create and edit only (name, category, description, specs, price, stock, status). No delete; "remove" is `status=discontinued`, which the agent already reports. Seed rows (`source='seed'`) are read-only from the screen, so nobody can wipe or vandalise the case catalog.
  - *Validation:* a pydantic body at the edge (lengths, price > 0 with two decimals, stock ≥ 0, known category, status enum, specs as a small flat string map) plus the DB `CHECK`s. JSON only (the existing `require_json` guard); no file upload in the first cut, so the CSV upload and file-parsing risks (OWASP File Upload cheat sheet, https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) do not apply.
  - *Limits:* the existing in-memory limiter, e.g. 10 writes/min per login and a cap of 200 admin-created rows.
  - *Audit:* `catalog_audit(at, actor, action, product_id, after jsonb)` in the same transaction.
  - *Reset:* `make ingest` (or a CLI `emporio reset-demo-catalog`) deletes `source='admin'` rows and re-seeds; the hosted demo can run it after the evaluation window.
  - *Sandbox per session* (admin rows visible only to their session) was considered: it needs a session filter in every query and every test. Not worth it for the demo; additive-only plus seed protection plus reset covers the "evaluator wipes the catalog" risk.
- **Cache invalidation:** drop the product cache. Every tool call reads the rows it needs by id or by search (one query, ~1–2 ms locally plus one ~80 ms RTT on Modal), so a new product is visible to the next turn with nothing to invalidate. Categories (9 rows) may stay cached per process; an admin category edit is out of scope. The API runs one container (`max_containers=1`), and even with more containers the DB is the single source, so nothing goes stale.

## 6. Local probes
Setup: the §8 schema in a scratch database; the 65 real products plus 50,000 synthetic ones generated from them (brand swapped within the category's real-world brands, random model codes like `KX-472CE`, colours, prices ×0.5–1.8, 90% active, many out of stock), so the real products sit among close near-duplicates. Real e5-small embeddings for every row. 30 labelled queries (§4).

### Retrieval quality at 65 rows (today's catalog)
| ranker | code h@1 / h@5 (11) | typo h@1 / h@5 (7) | meaning h@1 / h@5 (12) | all h@1 / h@5 |
|---|---|---|---|---|
| today's difflib grader (`domain/search.py`) | 10 / 10 | 6 / 7 | 6 / 6 | 0.73 / 0.77 |
| FTS only | 11 / 11 | 4 / 5 | 8 / 10 | 0.77 / 0.87 |
| trigram only | 10 / 10 | 5 / 5 | 0 / 0 | 0.50 / 0.50 |
| vector only | 11 / 11 | 6 / 7 | 8 / 10 | 0.83 / 0.93 |
| FTS + vector (RRF) | 11 / 11 | 6 / 7 | 8 / 11 | 0.83 / 0.97 |
| FTS + trigram + vector (RRF) | 11 / 11 | 6 / 7 | 8 / 11 | 0.83 / 0.97 |

- The difflib grader misses 6 meaning queries outright (NoMatch) and "quanto custa o takamine gd20" (filler words; the agent normally passes a cleaned query, so that one is partly unfair). It is a grader, not a retriever.
- The only hybrid miss at k=5 is "instrumento pequeno de quatro cordas pra levar em viagem" (wants any ukulele; the descriptions never say "quatro cordas" or "viagem" in a way e5 links).
- At 65 rows trigram adds nothing over FTS + vector; its value shows at scale (next table).

### Retrieval quality at 50,065 rows (same 30 queries, real products among synthetic near-duplicates)
Meaning queries cannot be scored by product id at this size: every real product has hundreds of synthetic twins with the same description, which are equally right answers. So meaning is scored as the share of the top 5 that lies in the expected category; model-code and typo queries (18) still name one product and are scored by id.

| ranker | code + typo h@1 / h@5 (18) | meaning: right category in top 5 | meaning by id h@5 (12) |
|---|---|---|---|
| FTS only | 12 / 13 | 0.73 | 9 |
| trigram only | 15 / 15 | n/a (matches nothing) | 0 |
| vector only | 3 / 3 | 0.75 | 0 |
| FTS + vector (RRF) | 10 / 13 | 0.77 | 9 |
| **FTS + trigram + vector (RRF)** | **14 / 18** | **0.77** | 9 |

- **Vector alone collapses on names and codes at scale** (3/18): "Yamaha C40" sits among hundreds of "Yamaha XX-123 Nylon" twins with near-identical vectors. This is the main reason the market keeps a lexical side.
- **Trigram is what fixes codes and typos at scale**: FTS + vector reaches 13/18 at k=5; adding trigram reaches 18/18 ("takamine gd 20", "yamah c70", "telecastr", "stratocastr", "Yamaha C40"). At 65 rows it changed nothing; at 50k it is the difference.
- Variant tested: FTS with AND first and OR only when AND matches nothing ("AND→OR") raised code + typo h@1 from 14/18 to 16/18 with the same h@5; pure AND drops h@5 to 15/18. Worth trying in the eval, not required.
- Hybrid misses at k=5 (by id): "instrumento pequeno de quatro cordas pra levar em viagem", "contrabaixo de 5 cordas", "violão folk com captação para tocar ao vivo"; all three return the right category with twins ahead of the real product.

### Latency and the filtered-HNSW pitfall at 50,065 rows (local, no RTT; 60 runs per row)
Filters: `none`; `avail` (status active and stock > 0, 70% of rows); `ukulele+avail+<=600` (category 9, available, final price ≤ R$ 600 after promotion, **8.6% of rows**). Each branch fetches 40, RRF returns 10. The Mac was also running Langfuse, Kafka and a k8s node, so absolute numbers are noisy (repeat runs of the same query moved p50 between 17 and 61 ms); compare rows within the table.

| query | filter | `hnsw.iterative_scan` | p50 ms | p95 ms | fewest rows returned (of 10) |
|---|---|---|---|---|---|
| vector | none | off | 1.1 | 3.7 | 10 |
| vector | avail | off | 0.7 | 1.3 | 10 |
| vector | 8.6% filter | **off** | 0.6 | 1.4 | **0** |
| vector | 8.6% filter | relaxed_order | 27.6 | 59.6 | 8 |
| FTS + vector | none | relaxed_order | 15.7 | 85.6 | 10 |
| FTS + trigram + vector | none | relaxed_order | 34.0 | 105.2 | 10 |
| FTS + trigram + vector | avail | relaxed_order | 17.0 | 46.8 | 10 |
| FTS + trigram + vector | 8.6% filter | relaxed_order | 30.7 | 77.8 | 8 |
| same, filter as `id IN (SELECT ... )` subquery | 8.6% filter | relaxed_order | 49.9 | 136.7 | 8 |

- **The pitfall is real and the fix works.** Without iterative scans the filtered vector query returned **0 rows** for some queries and its recall@10 against an exact scan was **0.06**; with `relaxed_order` it returned at least 8 of 10 and recall rose to **0.62**. "Fewest 8" means at least one query found fewer than 10 vector neighbours inside `hnsw.max_scan_tuples` (20,000); RRF with FTS/trigram still fills the list.
- HNSW recall@10 against exact search, unfiltered, by `hnsw.ef_search`: 0.46 (40), 0.67 (100), 0.73 (200), with vector latency 2.5–4.4 ms in all three. Set overlap understates recall here because the synthetic twins sit at near-identical distances; still, **`ef_search = 100`** is nearly free and is the recommended setting.
- **The FTS branch is the slow one.** The OR-ed tsquery for "violão de nylon para iniciante" matches 37,612 of 50,065 rows, and `ts_rank_cd` scores all of them: FTS alone p50 24.5 ms, p95 284 ms (`ts_rank`: 13.0 / 223 ms). A precise query ("takamine gd 20") matches 1,797. Hybrid p95 stays at ~50–140 ms because the other branches are cheap. At 100k+ use AND→OR (above) or a `ts_rank` cap before reaching for BM25.
- The `id IN (SELECT ...)` form is ~60% slower than inlining the predicate in each branch, though `EXPLAIN` showed HNSW used in both. Inline it (build the predicate once in Python).
- Plans: `EXPLAIN` of the 3-branch query used `products_embedding_idx`, the two trigram GIN indexes and the tsv GIN; execution 19.4 ms for "takamine gd 20" with the `avail` filter.
- **Today's difflib grader over the whole catalog does not scale**: run on the 50,065 rows, `domain/search.py` took **p50 1.5 s, max 7.4 s** per query (12 queries). Over a pool of 20 rows its cost is negligible (not measured; today it runs over 65 rows).

### Bulk load and the real-time write path
- Bulk: embedding 50,065 documents took 850 s (59/s, CPU shared with another run; ~100/s alone). `COPY` of the rows 5.3 s. Index builds: tsv GIN 0.4 s, each trigram GIN 0.3 s, **HNSW 14.0 s**. Table + indexes 260 MB, of which HNSW 98 MB (`maintenance_work_mem` default).
- Real-time path, one product: embed the passage **~9 ms** warm (17.8 ms for the first call), upsert row + vector **~7 ms**; a price/stock-only update **4.3 ms** with no re-embed.
- A new product ("Cavaquinho Rozini Choro Profissional RC-77X", a word no seed product uses) was found by the very next hybrid query: rank 1 for "cavaquinho", "cavaquinho profissional" and its full name, rank 2 for "cavaquinho para roda de choro" and for "rc77x" (via trigram). The **vector branch alone missed it** for "cavaquinho" among 50k violões; the lexical branches carried it. A batch of 20 near-identical new cavaquinhos competing for a generic query only got 10 of them into the top 20, which is expected ranking, not a visibility gap.
- Visibility needs no cache step: the HNSW and GIN indexes are updated in the insert transaction (GIN through its pending list, which searches also read).

### What the probes did not cover
- Railway itself (PG 18, network): not probed; add the ~80 ms RTT per query from `docs/scaling-and-cost.md`. `pg_trgm` availability on the Railway service is unconfirmed (one SQL line to check).
- Synthetic rows are template mutations of the 65 real ones, so the vocabulary is narrow; real 50k catalogs have more diverse text, which usually helps lexical search and makes vectors less crowded. Treat the scale table as a stress test of near-duplicates, not a forecast.

## 7. Migration plan from CSV
- **Tables** (migration `006_catalog.sql`): `categories`, `products` (columns as in §8, plus `source text NOT NULL DEFAULT 'seed'`, `embedded_hash text`, `updated_at`), `promotions`, `catalog_audit`. A later migration drops `product_embeddings` once nothing reads it (or keep it until the PR is merged; it is re-derivable).
- **Seed** in `emporio.ingest` (already the data composition root): read the CSVs with the existing parser (`CsvCatalogRepository` stays, as the seed source), `INSERT ... ON CONFLICT (id) DO UPDATE` for `source='seed'` rows, embed only rows whose `embedded_hash` changed. Idempotent: a second `make ingest` writes nothing new and embeds nothing. 65 rows embed in ~2 s.
- **Orders stay on CSV.** `order_items` reference product ids; `tools.py` gets product names by ids (`names_for(ids)`) instead of iterating the catalog.
- **Ports:**
  - `CatalogRepository` becomes: `get(id) -> Product | None`, `get_many(ids)`, `categories()`, `promotions_for(ids)`, `promoted()` (available products with an active promotion), and `search(query, filters, k) -> Sequence[Product]` (the hybrid retrieval). `ProductIndex` merges into it (one adapter, one table) and `RecommendProducts` calls `search` with `available=True`.
  - A `CatalogWriter` port (`upsert(product) -> Product`) used by an `UpsertProduct` use case; the Pg adapter builds the document, embeds when the hash changed and writes row + audit in one transaction.
- **Tests (`make test` stays DB-free):**
  - `FakeCatalogRepository` implements the new methods in memory; its `search` returns every product passing the filters, so the existing use-case and tool tests keep today's behaviour (the domain grader does the work, as now).
  - New unit tests: `UpsertProduct` validation, the NoMatch → fused-candidates fallback, admin route auth (401/403) and validation (422) with a fake use case.
  - New `@pytest.mark.postgres` tests with the deterministic `HashEmbedder` fake: seed idempotency, each filter (category, availability, final price with a promotion), model-code and typo hits through FTS/trigram (no real model needed), "upsert then search finds it", price-only update does not re-embed.
  - Eval: `products_retrieval.toml` with real e5 under `make evals`, hit@5 ≥ 0.9.
- **MCP** uses `build_toolbox`, so it gets the DB catalog for free and stays read-only.

## 8. Recommended design
One `products` table holds facts and search fields; one SQL statement retrieves; the pure domain grades; the admin writes synchronously.

```sql
-- 006_catalog.sql (sketch)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE TABLE categories (id int PRIMARY KEY, name text NOT NULL, description text NOT NULL);
CREATE TABLE products (
  id int PRIMARY KEY,                       -- seed keeps CSV ids; admin rows from a sequence starting at 100000
  name text NOT NULL CHECK (length(name) BETWEEN 2 AND 120),
  category_id int NOT NULL REFERENCES categories,
  description text NOT NULL CHECK (length(description) <= 2000),
  specs jsonb NOT NULL DEFAULT '{}',
  price numeric(12,2) NOT NULL CHECK (price > 0),
  stock int NOT NULL CHECK (stock >= 0),
  status text NOT NULL CHECK (status IN ('active','discontinued','coming_soon')),
  source text NOT NULL DEFAULT 'seed' CHECK (source IN ('seed','admin')),
  search_doc text NOT NULL,                 -- "{name}. {category}. {description} {k: v; ...}", built by the app
  embedding vector(384),                    -- NULL until embedded; FTS and trigram still find the row
  embedded_hash text,
  updated_at timestamptz NOT NULL DEFAULT now(),
  tsv tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('portuguese', f_unaccent(name)), 'A') ||
    setweight(to_tsvector('portuguese', f_unaccent(search_doc)), 'B')) STORED,
  name_key text GENERATED ALWAYS AS (lower(f_unaccent(name))) STORED,
  code_key text GENERATED ALWAYS AS (regexp_replace(lower(f_unaccent(name)), '[^a-z0-9]', '', 'g')) STORED
);
CREATE INDEX products_tsv_idx  ON products USING gin (tsv);
CREATE INDEX products_name_trgm ON products USING gin (name_key gin_trgm_ops);
CREATE INDEX products_code_trgm ON products USING gin (code_key gin_trgm_ops);
CREATE INDEX products_embedding_idx ON products USING hnsw (embedding vector_cosine_ops);
CREATE INDEX products_category_idx ON products (category_id);
CREATE TABLE promotions (id int PRIMARY KEY, product_id int NOT NULL REFERENCES products,
  percent numeric(5,2) NOT NULL CHECK (percent > 0 AND percent < 100), label text NOT NULL, active boolean NOT NULL);
CREATE INDEX promotions_active_idx ON promotions (product_id) WHERE active;
CREATE TABLE catalog_audit (id bigserial PRIMARY KEY, at timestamptz NOT NULL DEFAULT now(),
  actor text NOT NULL, action text NOT NULL, product_id int NOT NULL, after jsonb NOT NULL);
```

The hybrid query is the one measured in §6 (`rankers.py` in the probe). Run it in a transaction with `SET LOCAL hnsw.iterative_scan = relaxed_order` and `SET LOCAL hnsw.ef_search = 100`. `{flt}` is one predicate string built once in Python and inlined into all three branches, because the `id IN (SELECT ...)` form measured ~60% slower. The query expressions are inlined rather than read from a CTE so the planner sees constants and uses the GIN indexes. `%%` is psycopg's escaped `%`.

```sql
-- {flt}, inlined in every branch:
--   (%(category_id)s::int IS NULL OR p.category_id = %(category_id)s)
--   AND (NOT %(available)s OR (p.status = 'active' AND p.stock > 0))
--   AND (%(max_price)s::numeric IS NULL OR p.price * (1 - coalesce(
--         (SELECT max(x.percent) FROM promotions x WHERE x.product_id = p.id AND x.active), 0) / 100)
--       <= %(max_price)s)
WITH fts AS MATERIALIZED (
  SELECT p.id, row_number() OVER (ORDER BY ts_rank_cd(p.tsv, q.ts) DESC, p.id) AS r
  FROM products p,
       (SELECT replace(plainto_tsquery('portuguese', f_unaccent(%(text)s))::text, ' & ', ' | ')::tsquery AS ts) q
  WHERE p.tsv @@ q.ts AND {flt}
  ORDER BY ts_rank_cd(p.tsv, q.ts) DESC, p.id LIMIT 40),
trgm AS MATERIALIZED (
  SELECT p.id, row_number() OVER (ORDER BY greatest(
           word_similarity(lower(f_unaccent(%(text)s)), p.name_key),
           word_similarity(regexp_replace(lower(f_unaccent(%(text)s)), '[^a-z0-9]', '', 'g'), p.code_key)) DESC, p.id) AS r
  FROM products p
  WHERE (lower(f_unaccent(%(text)s)) <%% p.name_key
         OR regexp_replace(lower(f_unaccent(%(text)s)), '[^a-z0-9]', '', 'g') <%% p.code_key)
    AND {flt}
  ORDER BY r LIMIT 40),
vec AS MATERIALIZED (
  SELECT p.id, row_number() OVER (ORDER BY p.embedding <=> %(embedding)s, p.id) AS r
  FROM products p WHERE p.embedding IS NOT NULL AND {flt}
  ORDER BY p.embedding <=> %(embedding)s LIMIT 40),
fused AS (
  SELECT id, sum(1.0 / (60 + r)) AS score
  FROM (SELECT id, r FROM fts UNION ALL SELECT id, r FROM trgm UNION ALL SELECT id, r FROM vec) u
  GROUP BY id)
SELECT p.id, p.name, p.category_id, p.description, p.specs, p.price, p.stock, p.status,
       fused.score, best.id AS promo_id, best.percent AS promo_percent, best.label AS promo_label
FROM fused JOIN products p USING (id)
LEFT JOIN LATERAL (SELECT x.id, x.percent, x.label FROM promotions x
                   WHERE x.product_id = p.id AND x.active
                   ORDER BY x.percent DESC, x.id LIMIT 1) best ON true   -- same tie rule as best_active_promotion
ORDER BY fused.score DESC, p.id
LIMIT %(k)s;   -- k = 20 for the grader pool, `limit` for recommend_products
```

The sketch was run as written (filter substituted) against the 50k scratch database: "takamine gd 20" (available only) returns the real GD20 at rank 3, behind two synthetic "Takamine GD-xxx" twins, which is why the grader stays (it makes GD20 Exact by its glued code); "ukulele com som mais grave" with category 9, available and ≤ R$ 600 returns the real Kala KA-B Barítono first, then tenor and baritone ukuleles under the ceiling.

Flow per tool call: embed the query (~4 ms) → one SQL round trip → `Product` + best promotion → pure grader → `search_json`. `recommend_products` is the same query with `available=True` and no grader.

## 9. Proposed task breakdown (~4.5 h)
| # | Task | TDD pair(s) | Estimate |
|---|---|---|---|
| 1 | Migration `006_catalog.sql` (+ `pg_trgm`), migration test | `test(catalog): catalog tables migrate (red)` / `feat` | 25 min |
| 2 | Seed in `ingest.py` (idempotent upsert, hash-gated embedding), integration test | red/green | 35 min |
| 3 | `PgCatalogRepository`: `get`, `get_many`, `categories`, `promotions_for`, `promoted`, `search` (hybrid SQL above); postgres tests per filter, code/typo hit, NULL embedding still found | 2 pairs | 70 min |
| 4 | Port and use cases: new `CatalogRepository` methods, `SearchProducts` = search pool → grader (+ fallback), `RecommendProducts` on `search`, `GetProduct`/`ListPromotions` by query; fake repo; `tools.py` names/categories by ids; bootstrap wiring | 2 pairs | 60 min |
| 5 | `UpsertProduct` + `CatalogWriter` (sync embed, audit, `source='admin'`, row cap); admin login role, `POST/PUT /api/admin/products`, rate limit; tests for 401/403/422 | 2 pairs | 50 min |
| 6 | Minimal React admin form (create/edit, list of admin rows) | `check-web` | 30 min |
| 7 | `products_retrieval.toml` + eval test; `make evals` on Gemini for the 22 golden cases; README + spec ruling line; scaling note | — | 30 min |

If time runs short, cut in this order: task 6 (use the API from curl / Swagger in the demo), then the edit path in task 5 (create only).

## 10. Risks
- **Behaviour drift in the golden cases.** The grader now sees a pool of 20 instead of the whole catalog, and availability/price move into SQL. At 65 rows the pool covers everything plausible, but `catalogo_violoes` (35 violões, grader sorts Candidates by price and the serializer keeps 8) could show a different 8. Mitigation: rerun `make evals` before merging; if needed raise the pool for category-only queries.
- **Planner choices.** `EXPLAIN` showed HNSW and all GIN indexes in use at 50k, but at 65 rows the planner will seq-scan (correct, sub-millisecond). Tests must check results, never plans (as in phase 3). With very selective filters and few matches inside `hnsw.max_scan_tuples`, the vector branch returns fewer than 40; RRF still fills from the lexical branches.
- **FTS tail latency on broad queries** at 50k (p95 up to ~280 ms for the FTS branch alone when an OR-ed query matches 75% of rows). Fine at 65 rows and acceptable at 50k behind an 80 ms RTT; at 100k+ switch to AND→OR or BM25.
- **`pg_trgm` missing on Railway** (unconfirmed). Mitigation: check before merging; at 65 rows FTS + vector scored the same as the three-branch query, so the demo survives without it, but at 50k trigram is what took code + typo hit@5 from 13/18 to 18/18 (§6).
- **Hosted demo integrity.** An evaluator with the admin credential can still add junk products that the agent will then recommend. Mitigation: seed rows protected, row cap, audit, reset command; hand out the admin credential separately.
- **Latency on Modal** is one extra ~80 ms round trip per catalog read that used to be in memory; a turn with three catalog tool calls adds ~0.25 s. Acceptable against a 6 s Gemini turn; co-locating the DB is the fix already listed in `scaling-and-cost.md`.
- **Embedding failures on write** (model not loaded, OOM): with the recommended option the row is still written with `embedding NULL` and found by FTS/trigram, and an `ingest` run back-fills it (decision 5).
- **Known semantic limit of e5-small:** "algo pra tocar MPB em casa" lands near electric instruments (Telecaster, Music Man bass), with the old pure-vector index too, and down-weighting FTS/trigram makes it worse. The `recomendacao_mpb` golden case is therefore graded on store knowledge (any available nylon violão, no electric guitar or bass). Candidate fixes later: a reranker, or category hints in the product embedding text.
- **Spec scope creep.** The admin screen is new surface area two days before delivery; it must be explained in the README as the store's back office, not as an agent capability.

## Owner decisions
1. **Search stack:** FTS + `pg_trgm` + pgvector with RRF in one SQL query (recommended), FTS + vector only (drop trigram if Railway lacks it), or ParadeDB BM25 (new AGPL image service).
   Recommended: FTS + `pg_trgm` + pgvector (RRF k = 60).
   Answer (owner, 2026-11-07): FTS + `pg_trgm` + pgvector (RRF k = 60); `pg_trgm` 1.6 confirmed available on Railway.
2. **Grading:** keep today's pure domain grader over the hybrid pool of 20 (recommended; keeps Exact/Candidates semantics and its 36 tests), or let the SQL score alone decide Exact.
   Recommended: keep the domain grader.
   Answer (owner, 2026-11-07): keep the domain grader.
3. **Availability filter in SQL** (with `hnsw.iterative_scan = relaxed_order`), superseding the phase 3 "filter after retrieval" rule.
   Recommended: yes, in SQL.
   Answer (owner, 2026-11-07): yes, in SQL.
4. **Embedding on write:** synchronous in the admin request (recommended at ≤ 200 admin rows), or a queue/outbox worker.
   Recommended: synchronous; bulk loads through `make ingest`.
   Answer (owner, 2026-11-07): synchronous in the request; bulk loads through `make ingest`.
5. **If the embedding fails on an admin write:** save the row with `embedding NULL` (found by text search; back-filled later), or reject the write.
   Recommended: save with NULL and log.
   Answer (owner, 2026-11-07): save with NULL and log.
6. **Admin access in the hosted demo:** separate admin credential (recommended), admin role for the demo login, or admin only locally (`make up`).
   Recommended: separate credential, given to evaluators in the delivery note.
   Answer (owner, 2026-11-07): any logged-in demo user may create products (owner, 2026-11-07); protect it with a per-session write rate limit and server-side validation.
7. **Admin capabilities:** create + edit admin rows only, seed rows read-only, no delete (recommended); or full edit of seed rows too (e.g. change a price live in the demo).
   Recommended: create + edit; allow price/stock edits on seed rows only if the demo needs the "price changed, agent sees it" moment.
   Answer (owner, 2026-11-07): create + edit own rows only, seed rows read-only, no delete, one product per request.
8. **Bulk upload:** JSON form for one product (recommended for this delivery) or CSV upload.
   Recommended: one product per request; CSV later.
   Answer (owner, 2026-11-07): one product per request; no CSV upload.
9. **Reset of the hosted catalog:** manual `make ingest` reset after the evaluation, or an automatic nightly reset.
   Recommended: manual, documented.
   Answer (owner, 2026-11-07): manual `make ingest` reset after the evaluation, documented.
10. **`product_embeddings` table:** drop it in this PR or keep it until after delivery.
    Recommended: drop in a follow-up migration in this PR once nothing reads it.
    Answer (owner, 2026-11-07): drop it in this PR once nothing reads it.

Also decided: the README cites the research probe numbers for scale; no benchmark script is committed.
