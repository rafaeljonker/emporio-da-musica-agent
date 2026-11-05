# Phase 3 research: policy RAG, embeddings, pgvector, store hours

Date: 2026-11-05. PyPI versions fetched 2026-11-05 from `https://pypi.org/pypi/<name>/json`. Timings were measured on the owner's Apple Silicon Mac (Python 3.12, warm disk cache), not on Linux or Modal. Anything not verified is marked "unconfirmed". Scratch scripts were not committed.

## 1. PDF extraction and chunking
- The PDF is `data/políticas_da_loja.pdf` (`emporio.paths.POLICIES_PDF`). It has 8 A4 pages and was produced by "Skia/PDF m150 Google Docs Renderer" (`pdfinfo`). Page 1 is a cover page. Every later page carries the header "Empório da Música Manual de Políticas e Procedimentos" and the footer "Página N".
- I ran all three libraries on the real file. Times include the import.
  - **pypdf 6.21.4** (BSD-3, https://pypi.org/project/pypdf/) is unusable on this file. Every word comes out on its own line (`'3.1\n \nRegras\n \nde\n...'`), so no heading can be detected.
  - **pdfplumber 0.11.10** (MIT; it depends on pdfminer.six 20260107, MIT, and pypdfium2) gives clean lines: `'3.1 Regras de Parcelamento\n• Parcelamento em até 3x: ...'`. The hours table comes out as `Segunda a Sexta-feira 09:00 às 18:00`. Took about 1.5 s.
  - **PyMuPDF 2.1** gives clean text, but table cells are split across lines and bullets carry `​`. Its license is **AGPL-3.0 or commercial** (PyPI metadata), so it is ruled out.
- A naive heading regex `^\d+(\.\d)?\.?\s+` produces false positives. With pdfplumber, the numbered steps of 7.2 ("1. Saudação" … "5. Fechamento") match. With PyMuPDF, table cells such as "5 a 12 dias" match. The fix is a **sequence check**: a top-level heading `N. Title` must have N equal to the previous top-level number plus 1, and a subsection `N.M Title` must have N equal to the current top-level number. Also drop the header and footer lines, skip page 1, and strip `​`.
- Proposed rule: **one chunk per numbered subsection**. A top-level section's intro paragraph (1, 3, 4, 7) becomes its own chunk. Top-level sections with no subsections (2, 9, 10) are one chunk each. Headings with no body (5, 6, 8) are dropped. The embedded text is `"{top title} > {N.M} {sub title}\n{body}"`. Store `section_id`, `title` and `body` separately so answers can cite "seção 4.1".
- Result on the real file: **25 chunks**: 1, 1.1, 1.2, 2, 3, 3.1, 4, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 6.1, 6.2, 7, 7.1, 7.2, 7.3, 8.1, 8.2, 8.3, 9, 10. Sizes range from 144 to 786 characters, average 394. The longest is about 250 tokens, well under e5's 512-token limit, so nothing needs to be split.
- Layering: "PDF to lines" is infrastructure (`pdf_sections.py`, pdfplumber). "Lines to sections" is a pure function and can live in `policies/domain`, with unit tests on a list of strings.
- Data quirks to document as assumptions:
  - The WhatsApp number is **(67) 3341-4444** on the cover and in 1.2, but **(67) 3321-4500** in section 7.
  - The e-mail in 1.2 is `contato@empóriodamusica.com.br` (with an accent), but on the cover it is `contato@emporiodamusica.com.br`.

**Recommendation:** pdfplumber, sequence-checked heading parser, 25 chunks (one per numbered subsection, prefixed with the parent title).

## 2. Embeddings: `intfloat/multilingual-e5-small`
- Model card (https://huggingface.co/intfloat/multilingual-e5-small):
  - License MIT, 12 layers, 384 dimensions, input truncated at 512 tokens.
  - Every input needs the `"query: "` or `"passage: "` prefix ("otherwise you will see a performance degradation").
  - Pooling is the mean over tokens, followed by L2 normalization.
  - Cosine scores "distribute around 0.7 to 1.0" (the model was trained with a low temperature). So a relevance cut-off has to be calibrated on our eval, not set to something like 0.5.
- The HF repo ships `onnx/model.onnx` (FP32, 470 MB on disk) plus `model_O4.onnx` and `model_qint8_avx512_vnni.onnx` (HF API, `siblings`).
- **fastembed 0.9.1** (Apache-2.0, https://github.com/qdrant/fastembed):
  - Its built-in model list has `multilingual-e5-large` but **not e5-small** (checked with `TextEmbedding.list_supported_models()`).
  - The README's own `add_custom_model` example uses exactly `intfloat/multilingual-e5-small` with `pooling=PoolingType.MEAN, normalization=True, dim=384, model_file="onnx/model.onnx"`. I ran it: the output is 384-dimensional with norm 1.0.
  - Runtime stack: onnxruntime 1.31.1, tokenizers, huggingface-hub and numpy. No torch.
  - Measured: venv 141 MB, import 0.45 s, model load 1.2 s, about 5 ms per query on CPU.
  - The onnxruntime manylinux x86_64 wheel is 22.7 MB.
- **sentence-transformers 6.2.0** with torch 2.15.0:
  - Measured on Mac: venv 913 MB, warm import 6.1 s, load 4.1 s, 15 ms per query.
  - On Linux, the PyPI torch wheel alone is 514 MB, and it depends on `nvidia-*-cu13` packages. A CPU-only build needs the PyTorch CPU index, which is extra uv configuration.
- **Plain onnxruntime with tokenizers** is what fastembed already does (mean pooling, normalization). Rewriting it would save one small pure-Python wheel (0.1 MB). Not worth it.
- Docker and Modal image size: about 150 MB of libraries plus the 470 MB model.
  - Download the model at image build time (or into a Modal Volume) and set `cache_dir`. Then cold start never hits Hugging Face. The first download took about 11 s here.
  - Ingestion and query **must use the same model file**. Pin `model_file="onnx/model.onnx"` and the HF revision.

**Recommendation:** fastembed 0.9.1 with `add_custom_model` for e5-small FP32 ONNX, wrapped in one module that adds the `query:`/`passage:` prefixes; no torch.

## 3. pgvector
- pgvector **0.8.7** (https://github.com/pgvector/pgvector).
  - Docker tags follow `pgvector/pgvector:pgNN` and `0.8.7-pgNN` (optionally `-trixie` or `-bookworm`).
  - The cosine distance operator is `<=>`. Index with `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)`.
  - HNSW defaults: `m=16`, `ef_construction=64`, `hnsw.ef_search=40`. `vector` supports up to 2,000 dimensions in HNSW, so 384 is fine.
- Honest answer on the index:
  - Without an index, pgvector does an exact search with "perfect recall". At 25 + 65 rows a sequential scan is sub-millisecond, and the planner will usually ignore the index anyway.
  - Build the HNSW index anyway. It is one line, the phase 3 deliverable names it, and it documents the path to scale. But no test should assert that the index is used.
  - Pitfall: with an approximate index, a `WHERE` filter is applied **after** the index scan, so results can be sparse (README, "Filtering"). For `recommend_products`, do not filter on stock or status in SQL. Fetch the top k (10) by vector, then let the catalog use case filter for availability.
- pgvector-python **0.5.1** (MIT, https://github.com/pgvector/pgvector-python):
  - `from pgvector.psycopg import register_vector` then `register_vector(conn)`. The async variant is `register_vector_async`.
  - With a pool, register it in the `configure=` callback.
  - The `vector` extension must exist before you register, so run migrations first.
- psycopg **3.3.8** (`psycopg[binary]` bundles libpq, which suits slim images; LGPL-3.0, fine as an unmodified dependency) and psycopg-pool **3.3.3**.
  - **Sync vs async:** use sync for our adapters. LangGraph runs sync tools in a thread pool, the ingestion script is a batch job, and sync keeps the adapters and tests trivial.
  - Async only matters for the checkpointer in phase 4 (`AsyncPostgresSaver`). It can use its own `AsyncConnectionPool`.
- Schema, in the first migration:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  CREATE TABLE policy_chunks (section_id text PRIMARY KEY, title text NOT NULL, body text NOT NULL,
                              embedding vector(384) NOT NULL);
  CREATE INDEX policy_chunks_embedding_idx ON policy_chunks USING hnsw (embedding vector_cosine_ops);
  CREATE TABLE product_embeddings (product_id integer PRIMARY KEY, embedding vector(384) NOT NULL);
  CREATE INDEX product_embeddings_embedding_idx ON product_embeddings USING hnsw (embedding vector_cosine_ops);
  ```
- Ingestion is idempotent: `TRUNCATE` then `INSERT` in one transaction.
- Query: `SELECT section_id, title, body, 1 - (embedding <=> %s) AS score FROM policy_chunks ORDER BY embedding <=> %s LIMIT %s`.
- Products:
  - Embed `"passage: {name}. {category}. {description}"`. The 65 descriptions are 109–148 characters each.
  - Only `product_id` is stored next to the vector. Prices and stock always come from the CSV catalog.
- Where the embedder lives: the import-linter contract "Infrastructures are independent of each other" forbids `catalog.infrastructure` from importing `policies.infrastructure.e5_embedder`. Put it in a top-level `emporio/embeddings.py`, like `emporio/paths.py`, and add a forbidden contract so that only infrastructure may import it.

**Recommendation:** `pgvector/pgvector:0.8.7-pgNN` locally, `vector(384)` + HNSW cosine (built but not relied on), sync psycopg 3 + `register_vector` via pool `configure`, filtering after retrieval.

## 4. Migrations
- **alembic 1.20.1** (MIT) needs SQLAlchemy, which is not in our stack (and SQLAlchemy is in the forbidden list for domain). Too heavy for two or three SQL files.
- **yoyo-migrations 9.0.0** (Apache) is a real tool. It is still a new dependency for something about 25 lines replace.
- `docker-entrypoint-initdb.d` only runs on an empty local volume. It never runs on Railway, so it cannot be the mechanism.
- Plain `backend/migrations/NNN_name.sql` files plus a tiny runner:
  - The runner creates `schema_migrations(version text PRIMARY KEY, applied_at timestamptz DEFAULT now())`.
  - It applies the not-yet-applied files in sorted order, each in its own transaction.
  - Never use `CREATE INDEX CONCURRENTLY` in these files, because it cannot run inside a transaction.
- `make up` runs it as compose up, wait for `pg_isready`, `make migrate`, then `make ingest`. The same command works against Railway with `DATABASE_URL` set.

**Recommendation:** plain SQL files + a ~25-line psycopg runner (`make migrate`), no new dependency.

## 5. LangGraph Postgres checkpointer (sizing only)
- **langgraph-checkpoint-postgres 3.2.0** (MIT, https://pypi.org/project/langgraph-checkpoint-postgres/). "Call `.setup()` the first time." Manual connections need `autocommit=True` and `row_factory=dict_row`.
- `PostgresSaver.from_conn_string` opens its connection with `autocommit=True, prepare_threshold=0, row_factory=dict_row` (`langgraph/checkpoint/postgres/__init__.py` on main).
  - Note that `prepare_threshold=0` prepares every statement. psycopg docs say poolers are incompatible with prepared statements unless PgBouncer is 1.22 or newer with `max_prepared_statements` set (https://www.psycopg.org/psycopg3/docs/advanced/prepare.html). This matters only if a pooler is added later.
- `setup()` creates `checkpoint_migrations`, `checkpoints`, `checkpoint_blobs` and `checkpoint_writes`, plus thread_id indexes created `CONCURRENTLY` (that is why it needs autocommit).
  - These names do not clash with `policy_chunks`, `product_embeddings` or `schema_migrations`, so the DB is shared cleanly in the `public` schema.
  - Keep `setup()` out of our SQL migrations: call it from the migrate step in phase 4.

**Recommendation:** same database, no schema split; reserve nothing now beyond knowing phase 4 adds `setup()` to `make migrate`.

## 6. Hosted Postgres: Railway (owner decision)
- **The default Railway Postgres now ships pgvector.**
  - The template image is `ghcr.io/railwayapp-templates/postgres-ssl:<major>` (https://github.com/railwayapp-templates/postgres-ssl). It is built `FROM postgres:<major>-trixie`.
  - It installs `postgresql-<major>-pgvector=0.8.*` and pgaudit (`Dockerfile.17`, `Dockerfile.18`). The README says it is "a `CREATE EXTENSION` away".
  - Railway's own guide (https://docs.railway.com/guides/postgresql) still says the default template includes no extensions. That page looks stale.
  - **Verify in the owner's existing service:** `SELECT name, default_version FROM pg_available_extensions WHERE name='vector';`. A service created long ago may run an older image tag. If so, redeploy it on the current tag of the same major.
- Alternatives: a community template running `pgvector/pgvector:pg18` (https://railway.com/deploy/pgvector, "Brody's Projects", 2,056 deploys), or an image service with a volume.
  - Both **lack SSL**, because the official image has no SSL (postgres-ssl README).
  - They also bring the PG18 volume-path change: `PGDATA=/var/lib/postgresql/18/docker`, volume at `/var/lib/postgresql` (https://hub.docker.com/_/postgres).
  - Prefer the default plugin.
- Networking:
  - Inside the project, services use the private `DATABASE_URL`.
  - Modal is outside Railway, so it needs **Public Access**, which creates a TCP proxy like `shuttle.proxy.rlwy.net:15140` and fills `DATABASE_PUBLIC_URL` (https://docs.railway.com/reference/tcp-proxy).
  - Connect with `sslmode=require`. The certificate is generated by the image's `init-ssl.sh`, probably self-signed, so `verify-full` will likely fail (unconfirmed).
  - Proxy traffic is billed as egress at $0.05/GB, negligible here.
  - The DB is then reachable from the internet, so keep Railway's generated password and never commit the URL. Store it in the `emporio-db` Modal secret and the local `.env`.
- Connections:
  - Railway documents no proxy connection cap or idle timeout. Postgres' default `max_connections` is 100; the image setting is unconfirmed.
  - Plan for each Modal container to hold a psycopg pool of min 1 / max 4, plus the checkpointer pool. Ten warm containers would still be under 100.
  - **No pooler needed** at demo and load-test scale. Railway's PgBouncer guide targets HA setups.
- Do **not** enable Serverless (app sleeping) on the DB. It sleeps after 5–10 min without outbound traffic, and the first request after that hits a cold boot that may fail (https://docs.railway.com/reference/app-sleeping).
- Pricing (https://docs.railway.com/reference/pricing/plans):
  - Hobby is $5/month, which includes $5 of usage.
  - Usage rates: RAM $10/GB-month, vCPU $20/vCPU-month, volume $0.15/GB-month. The Hobby volume limit is 5 GB.
  - A small always-on Postgres at about 0.2–0.3 GB RAM and near-idle CPU should come to roughly $2–4/month, inside the included $5. This is an estimate, unconfirmed until it shows in the project's usage tab.
- Backups (https://docs.railway.com/reference/backups):
  - Volume backups can be manual or scheduled: daily (kept 6 days), weekly (27 days), monthly (89 days). They are incremental and billed at volume rates.
  - Our vectors are re-derivable with `make ingest`. Only phase-4 checkpoints and metrics would be lost, so one daily schedule is enough.
- Neon or Supabase are not needed: the owner already runs a Railway project, so one less account and no free-tier autosuspend to manage.

**Recommendation:** Railway's default Postgres plugin (postgres-ssl, pgvector 0.8.x) after verifying `pg_available_extensions`; public TCP proxy + `sslmode=require` from Modal; no pooler; no app sleeping; daily backup.

## 7. Store hours and "open now"
- What the PDF says (section 2):
  - Mon–Fri 09:00–18:00, Sat 09:00–13:00, "Domingo e Feriados: Fechado".
  - WhatsApp follows the same hours, "com respostas automáticas fora do expediente".
  - Hours "podem ser estendidos" on Black Friday, the store anniversary (August) and Christmas, announced on social media. The agent should say so and never promise extended hours.
  - Section 7.1: out of hours, the assistant must "informar o horário de retorno". So `store_now` returns `open: bool` plus `next_opening: datetime`.
- The PDF lists **no holiday dates**.
  - The `holidays` package (0.108, MIT) with `BR(subdiv="MS")` gives the national holidays plus "Criação do Estado" (10-11). It has no Campo Grande municipal holidays (city anniversary 08-26, unconfirmed).
  - A hard-coded `frozenset[date]` for 2025–2026 in infrastructure or config, injected into the pure domain function, needs no new dependency.
- Domain: `is_open(now: datetime, holidays) -> bool` and `next_opening(...)`, a pure weekly table. Boundaries: 09:00 is open; 18:00 is closed (end-exclusive, an assumption to document).
- Time zone: `America/Campo_Grande` is UTC-4 with no DST.
  - `shared/clock.py` already has `STORE_TZ` and a comment about tzdata. Its `Clock` exposes only `today()`, so `store_now` needs a `now()` added to the Protocol and to `FixedClock`.
  - If the OS has no tz database, `zoneinfo` raises; it falls back to the PyPI `tzdata` package (2026.6, Apache-2.0) (https://docs.python.org/3/library/zoneinfo.html).
  - Whether `python:3.12-slim` (trixie) and Modal's `debian_slim` ship `/usr/share/zoneinfo` is **unconfirmed**: Docker was not running, so I could not test it.
  - Adding `tzdata` as a runtime dependency removes the question.
- `DEFAULT_STORE_TODAY` = 2026-02-20 is a Friday. It falls after Carnaval (02-16/17, which is not a legal holiday in `holidays`), so the demo store is open at that date.

**Recommendation:** pure weekly-hours function + injected holiday set + `tzdata` runtime dependency; extend `Clock` with `now()`.

## 8. Testing strategy
- **Unit tests**, offline and fast:
  - The section parser runs on literal line lists, including the "1. Saudação" trap inside 7.2 and the header/footer noise.
  - `store_hours` covers the boundaries: 08:59, 09:00, 17:59, 18:00, Sat 13:00, Sunday, a holiday, and `next_opening` from Sat 13:00 to Mon 09:00.
  - `search_policies` and `recommend_products` run against an in-memory fake `PolicyIndex`/`ProductIndex` (a keyword-overlap fake is enough). The `PolicyIndex` port takes text and returns `PolicyChunk`s; the embedder stays inside the adapter, so application code never sees numpy.
- **Integration tests** on real Postgres, marked `@pytest.mark.postgres` (registered in `pyproject`), use a deterministic fake embedder (hash to 384-dimensional unit vectors). They test SQL, `register_vector`, idempotent ingest and the migration runner, without downloading 470 MB.
  - They skip when `DATABASE_URL` is unset, so `make check` stays offline.
  - `make test-pg` runs them against `docker compose`.
- **CI:**
  - Use a GitHub Actions **service container** `pgvector/pgvector:0.8.7-pgNN` with a `pg_isready` health check (Linux runner only; https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers). No new dependency.
  - testcontainers 4.15.0 (Apache) would add a dependency and Docker-socket handling for the same result, since `docker compose` already exists locally for `make up`.
- One **eval test** (see §9) uses the real e5 model. It is marked `eval`, runs in `make evals` and in a CI job with the HF cache keyed on the model revision, and is not part of `make check`.

**Recommendation:** fakes for unit tests, `postgres`-marked integration tests skipped without `DATABASE_URL`, GitHub service container in CI, no testcontainers.

## 9. Retrieval quality
- I measured pure vector search (e5-small via fastembed, the 25 chunks of §1, cosine, 20 pt-BR questions). It hit **13/20 at rank 1, 16/20 in the top 3 and 18/20 in the top 5**.
  - Misses at k=5: "vocês abrem domingo?" (wants 2; it returned 1.1, 4.3, ...), and "o produto esgotou, e agora?" (wants 7.3, which says "fora de estoque").
  - Weak at rank 1: "quero trocar a cor da guitarra" (4.3 lost to 4.2), "qual a garantia do instrumento?" (8.1 lost to 8.3).
  - The score gaps are tiny (0.83 vs 0.83), as the model card predicts.
- **Hybrid** search would add `to_tsvector('portuguese', unaccent(...))` with RRF in one SQL query. Postgres contrib `unaccent` is in both images (unconfirmed for Railway); it is not IMMUTABLE, so a generated column needs a wrapper function.
  - It would fix "domingo", a literal word in section 2. It would not fix "esgotou" vs "fora de estoque".
  - Hours questions go to the deterministic `store_now` tool anyway.
  - At 25 chunks, the cheaper lever is **k=4–5**: the LLM reads about 1.5k characters and picks.
- Minimal eval to include: `backend/evals/policies_retrieval.yaml` with about 20 `{question, expected_section}` pairs (the set above), and a test asserting hit@5 ≥ 0.9 and printing hit@1.
  - The same file calibrates any "no relevant policy" score cut-off. Do not hard-code one, because e5 scores sit at 0.7–1.0.

**Recommendation:** pure vector, k=5, plus the 20-question hit@5 ≥ 0.9 eval; add hybrid (FTS `portuguese` + unaccent, RRF) only if that eval fails.

## Recommended decisions for phase 3
1. pdfplumber with a sequence-checked section parser (pure, in domain): 25 chunks, title-prefixed, cited by section id.
2. fastembed 0.9.1 with e5-small ONNX (`add_custom_model`), model baked into the image; no torch. Lives in `emporio/embeddings.py`, used only by infrastructure.
3. psycopg 3.3 (sync) + psycopg-pool + pgvector 0.5.1; `vector(384)`, HNSW cosine; plain SQL migrations with a tiny runner; `make up` = compose, migrate, ingest.
4. Railway default Postgres (verify `vector` is available), public proxy with `sslmode=require`, no pooler, no sleeping, daily backup.
5. Store hours as a pure function, holidays injected, `tzdata` dependency, `Clock.now()`; retrieval eval gate hit@5 ≥ 0.9.

## Decisions to confirm with the owner
1. **Clock for "open now":** should it use the real wall clock (true opening hours for a visitor today), or `STORE_TODAY` (2026-02-20) plus the real time of day (consistent with the order windows)? Recommended: the real wall clock, documented.
2. **Holidays:** a hard-coded 2025–2026 list (national + MS + Campo Grande 08-26), or the `holidays` package (no municipal days)? Recommended: hard-coded, no dependency.
3. **Contact data conflict:** which WhatsApp number does the agent quote, (67) 3341-4444 (cover/1.2) or (67) 3321-4500 (section 7)? And should it use the accent-free e-mail?
4. **Hybrid search:** ship pure vector (k=5) and add hybrid only if the eval fails, or build hybrid now for the README story?

## Risks
- **Image size and cold start:** the 470 MB FP32 model plus about 150 MB of libraries. If it is not baked in, the first request downloads from HF (~11 s here, and rate limits apply). Mitigation: download at image build time and pin the revision.
- **Vectors out of sync:** a different model file or revision between ingest and query silently degrades search. Mitigation: store the model id and revision in a row checked at startup (or simply re-ingest on deploy).
- **Railway:** the existing DB service may run an older image without `vector`. The docs contradict the image repo. The public proxy exposes the DB to the internet. The certificate may be self-signed, which rules out `verify-full`.
- **Low score margins** in e5 make thresholds fragile. The k=5 approach depends on the LLM ignoring the irrelevant chunks; the evals in phase 4 must cover it.
- **Filtered queries on HNSW** return sparse results. Never put availability filters in the vector SQL.
- **Unverified tz database** in the slim images. Mitigation: the `tzdata` dependency.

## Owner decisions (2026-11-05)
- Hosted Postgres: Railway, in the owner's existing project.
- "Open now" uses the real wall clock (America/Campo_Grande); return windows keep `STORE_TODAY`. Documented in the README.
- Holidays: hard-coded 2025–2026 list (national, MS, Campo Grande) with a source per entry.
- WhatsApp quoted to customers: (67) 3341-4444 (cover and 1.2); the section 7 number is recorded as an assumption.
- Retrieval: hybrid now (pgvector + Postgres full-text `portuguese` with `unaccent`, fused by rank), measured against the pure-vector baseline on the 20-question eval.
