# Phase 3: Policy RAG, store hours and product recommendations — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** let the agent answer from the store manual and from open-ended product needs. This phase delivers:
- the policy PDF split into numbered sections;
- hybrid retrieval (pgvector + Portuguese full-text) behind a `PolicyIndex` port;
- a deterministic "open now" answer;
- a semantic `recommend_products(need)`;
- a local Postgres + pgvector with plain SQL migrations and one-command ingestion;
- a retrieval eval.

**Architecture:**
- **Domain** (`policies/domain`) is pure: the section parser, `PolicyChunk` and the store-hours rules.
- **Application** holds the ports `PolicyIndex` and `ProductIndex`, plus one use case per file. Application code never sees vectors.
- **Infrastructure** holds pdfplumber, the Postgres adapters (psycopg 3 sync + pgvector) and the hybrid SQL.
- **Shared technical modules** live at the top level next to `emporio/paths.py`: `emporio/embeddings.py`, `emporio/db.py` and `emporio/migrate.py`. Import-linter allows only infrastructure and composition roots to use them.
- **Composition root:** `python -m emporio.ingest`.

**Tech stack:**
- pdfplumber 0.11;
- fastembed 0.9 with `intfloat/multilingual-e5-small` ONNX (384 dims);
- psycopg[binary] 3.3 and psycopg-pool 3.3;
- pgvector (python) 0.5 and pgvector 0.8.7 (`pgvector/pgvector:0.8.7-pg17`);
- tzdata;
- docker compose;
- pytest markers `postgres` and `eval`;
- stdlib `tomllib` for eval data.

**Spec:** `docs/superpowers/specs/2026-11-05-emporio-agent-design.md` §5 (embeddings, Railway), §7.1, §7.2, §7.3, §7.7, §7.9 (phase 3 row), §7.14. **Research and owner decisions:** `docs/research/fase-3.md`, which you must read; its "Owner decisions" section is binding.

## Global Constraints
- **Branch and commits:** branch `feat/policies-rag`. TDD pairs `test(<scope>): <behavior> (red)` then `feat(<scope>): <behavior>`; scopes are `policies`, `catalog`, `shared`, `db`, `ci`, `build`. Entity or config scaffolding goes in its own `chore`/`build` commit, never inside a `(red)` commit. Subject ≤ 72 chars, imperative. Every commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Gates:** `make check` is green on every non-red commit and stays **offline**:
  - `postgres` tests skip when `DATABASE_URL` is unset;
  - `eval` tests are excluded from `make check` (`-m "not eval"`).

  The pre-commit hook needs `backend/.venv/bin` on `PATH`; Task 1 fixes that in the Makefile.
- **Runtime dependencies** (exact floors): `pdfplumber>=0.11.10`, `fastembed>=0.9.1`, `psycopg[binary]>=3.3.8`, `psycopg-pool>=3.3.3`, `pgvector>=0.5.1`, `tzdata>=2026.6`. No torch, no sentence-transformers, no alembic, no SQLAlchemy, no testcontainers, no `holidays`, no PyYAML.
- **Layering:**
  - All 16 existing import-linter contracts stay kept.
  - `emporio.embeddings`, `emporio.db` and `emporio.migrate` join `emporio.paths` in the "Only infrastructure may use …" contract.
  - `numpy`, `fastembed`, `pdfplumber`, `pgvector` and `psycopg_pool` are added to the domain/shared denylist.
- **Embeddings:**
  - Model and file: `intfloat/multilingual-e5-small`, `model_file="onnx/model.onnx"`, mean pooling, L2-normalized, 384 dims.
  - Prefix every input with `"query: "` or `"passage: "`.
  - Ingestion and query use the same model and file.
- **Database:**
  - `DATABASE_URL` is the only connection setting.
  - Local: `postgresql://emporio:emporio@localhost:5434/emporio` (compose). Hosted: Railway via `DATABASE_PUBLIC_URL` with `sslmode=require` (phase 6).
  - Never commit a real URL or password. Compose's local password is a dev-only literal.
- **Retrieval:**
  - Policies use hybrid search: vector cosine rank + `portuguese` full-text rank over `f_unaccent(...)`, fused with RRF `1/(60 + rank)`, k = 5.
  - Products use vector only: top 10 by vector, availability filtered **after** retrieval, never in SQL, at most 5 returned.
- **Store hours** (policy section 2):
  - Mon–Fri 09:00–18:00, Sat 09:00–13:00, closed on Sundays and holidays.
  - Opening is inclusive and closing exclusive (09:00 open, 18:00 closed).
  - Time zone `America/Campo_Grande`. "Open now" uses the **real wall clock**; return windows keep `STORE_TODAY`.
- **Holidays:** a hard-coded `frozenset[date]` for 2025–2026 (national, MS, Campo Grande), with a source comment per entry, living in infrastructure and injected.
- **Contact data** (recorded for phase 4, not used in code here): WhatsApp (67) 3341-4444; the section-7 number (67) 3321-4500 is a documented assumption.
- **data/** is read-only; reach it only through `emporio.paths`.

## Review Focus
1. **Numbered steps inside a section** (7.2 "1. Saudação" … "5. Fechamento"). Expected: they stay inside chunk 7.2 and never start a new section. Test: Task 2 `test_numbered_steps_inside_subsection_are_not_headings`.
2. **Re-running ingestion.** Expected: identical row counts, no duplicates, no stale rows. Test: Task 7 `test_replace_all_is_idempotent` and Task 8 `test_product_index_replace_all_is_idempotent`.
3. **Recommendation hits a discontinued, `coming_soon` or zero-stock product.** Expected: never returned. Test: Task 8 `test_recommend_skips_unavailable_products`.
4. **"Tá aberto?" on Saturday at 13:00, on Sunday, or on the day before a holiday.** Expected: closed, with the correct next opening, skipping Sunday and holidays. Test: Task 3 `test_next_opening_skips_sunday_and_holiday`.
5. **Accent-free question** ("devolucao", "garantia do violao"). Expected: the full-text side still matches "devolução"/"violão". Test: Task 7 `test_full_text_matches_without_accents`.

---

### Task 1: dependencies, `Clock.now()`, contracts and Makefile PATH

**Files:**
- Modify: `backend/pyproject.toml` (deps, pytest markers, import-linter), `backend/uv.lock`, `Makefile`, `backend/src/emporio/shared/clock.py`
- Test: `backend/tests/unit/shared/test_clock.py`

**Interfaces:**
- Produces:
  - `Clock.now() -> datetime`, aware, in `STORE_TZ`.
  - `SystemClock.now()` returns the real time.
  - `FixedClock(fixed: date, at: time = time(12, 0))`. `now()` returns `datetime.combine(fixed, at, tzinfo=STORE_TZ)` and `today()` is unchanged.
  - Pytest markers `postgres` and `eval`.

- [ ] **Step 1: `build(backend)` commit.**
  - Add the runtime dependencies from Global Constraints (`uv add`).
  - Register the markers in `[tool.pytest.ini_options]`: `markers = ["postgres: needs DATABASE_URL", "eval: real model, run by make evals"]` and `addopts` += `-m "not eval"`.
  - Extend the contracts as Global Constraints says.
  - In the Makefile, prefix git-hook-sensitive targets so `pre-commit` resolves: `export PATH := $(CURDIR)/backend/.venv/bin:$(PATH)` at the top.
  - Run `make check`: green.
- [ ] **Step 2: failing tests** in `test_clock.py`:
  - `test_fixed_clock_now_is_aware_noon_in_store_tz`: `FixedClock(date(2026,2,20)).now() == datetime(2026,2,20,12,0,tzinfo=STORE_TZ)`;
  - `test_fixed_clock_now_uses_given_time`;
  - `test_system_clock_now_is_aware`: `tzinfo is not None` and `utcoffset() == timedelta(hours=-4)`.
- [ ] **Step 3:** run, expect FAIL. Commit `test(shared): clock exposes now (red)`.
- [ ] **Step 4:** implement. `make check` green. Commit `feat(shared): add Clock.now`.

### Task 2: policy sections (pure parser + PDF adapter)

**Files:**
- Create: `backend/src/emporio/policies/domain/policy_chunk.py`, `backend/src/emporio/policies/domain/sections.py`, `backend/src/emporio/policies/infrastructure/pdf_sections.py`
- Test: `backend/tests/unit/policies/test_sections.py`, `backend/tests/integration/test_policies_pdf.py`

**Interfaces:**
- Produces:
  - `PolicyChunk(section_id: str, title: str, parent_title: str | None, body: str)`, frozen and slotted. Its property `embedding_text -> str` is `f"{parent_title} > {section_id} {title}\n{body}"`, or `f"{section_id} {title}\n{body}"` when there is no parent.
  - `clean_lines(pages: Sequence[str]) -> list[str]`: drops page 1 (the cover), the header line "Empório da Música Manual de Políticas e Procedimentos", footer lines `Página N`, the zero-width space `​` and blank lines.
  - `parse_sections(lines: Sequence[str]) -> tuple[PolicyChunk, ...]`, the sequence-checked parser from research §1:
    - a top-level heading `N. Title` must have N equal to the previous top-level number plus 1;
    - a subsection `N.M Title` must have N equal to the current top-level number;
    - a top-level intro paragraph becomes its own chunk;
    - headings with no body are dropped.
  - `read_policy_chunks(pdf: Path = POLICIES_PDF) -> tuple[PolicyChunk, ...]` in infrastructure (pdfplumber `extract_text()` per page, then `clean_lines` and `parse_sections`), and `PdfPolicySource(pdf: Path = POLICIES_PDF)` with `chunks()` returning it (satisfies Task 6's `PolicySource`).

- [ ] **Step 1: failing unit tests** on literal line lists:
  - `test_subsections_become_chunks_with_parent_title`;
  - `test_top_level_intro_becomes_own_chunk`;
  - `test_heading_without_body_is_dropped`;
  - `test_numbered_steps_inside_subsection_are_not_headings`: lines for "7.2 Fluxo …" followed by "1. Saudação" … "5. Fechamento" produce exactly one chunk `7.2` whose body contains "Saudação";
  - `test_clean_lines_drops_cover_header_footer_and_zwsp`;
  - `test_embedding_text_format`.
- [ ] **Step 2: failing integration test** `test_real_pdf_yields_25_sections`: the ids are exactly `1, 1.1, 1.2, 2, 3, 3.1, 4, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 6.1, 6.2, 7, 7.1, 7.2, 7.3, 8.1, 8.2, 8.3, 9, 10`. Every body is 100–900 chars. Chunk `2` contains "09:00" and "Domingo".
- [ ] **Step 3:** run, expect FAIL. Commit `test(policies): section parser and real PDF (red)`.
- [ ] **Step 4:** implement. `make check` green. Commit `feat(policies): parse the store manual into sections`.

### Task 3: store hours and `StoreNow`

**Files:**
- Create: `backend/src/emporio/policies/domain/store_hours.py`, `backend/src/emporio/policies/application/store_now.py`, `backend/src/emporio/policies/infrastructure/holidays.py`
- Test: `backend/tests/unit/policies/test_store_hours.py`, `backend/tests/unit/policies/test_store_now.py`

**Interfaces:**
- Consumes: `Clock.now()` (Task 1).
- Produces:
  - `is_open(now: datetime, holidays: frozenset[date]) -> bool` and `next_opening(now: datetime, holidays: frozenset[date]) -> datetime`. When the store is open, `next_opening` returns `now`.
  - `StoreStatus(open: bool, now: datetime, next_opening: datetime)`, frozen and slotted.
  - `StoreNow(clock: Clock, holidays: frozenset[date])`, with `__call__() -> StoreStatus`.
  - `STORE_HOLIDAYS: frozenset[date]` in infrastructure, covering 2025–2026 with one source comment per line. It includes 2026-01-01, 2026-04-03 (Good Friday), 2026-04-21, 2026-05-01, 2026-09-07, 2026-10-11 (MS), 2026-10-12, 2026-11-02, 2026-11-15, 2026-11-20, 2026-12-25 and 2026-08-26 (Campo Grande, mark `# unconfirmed`), plus the 2025 equivalents.

- [ ] **Step 1: failing tests**, all in `STORE_TZ`, with `HOLIDAYS = frozenset({date(2026, 4, 21)})`:
  - `test_open_boundaries` (parametrized): Fri 2026-02-20 at 08:59 is closed, 09:00 open, 17:59 open, 18:00 closed;
  - `test_saturday_closes_at_13`: 12:59 open, 13:00 closed;
  - `test_sunday_closed`;
  - `test_holiday_closed`: Tue 2026-04-21 at 10:00;
  - `test_next_opening_from_saturday_afternoon_is_monday_9`: Sat 2026-02-21 13:00 gives Mon 2026-02-23 09:00;
  - `test_next_opening_skips_sunday_and_holiday`: with `frozenset({date(2026, 4, 20)})`, Sat 2026-04-18 15:00 gives Tue 2026-04-21 09:00;
  - `test_next_opening_before_opening_same_day`: Fri 07:00 gives Fri 09:00;
  - `test_store_now_uses_clock` (FixedClock at Sun 2026-02-22 10:00 gives `open=False`, next Mon 09:00);
  - `test_holiday_set_has_no_weekend_duplicates_and_covers_2026`, which asserts `date(2026, 12, 25) in STORE_HOLIDAYS`.
- [ ] **Step 2:** run, expect FAIL. Commit `test(policies): store hours and open now (red)`.
- [ ] **Step 3:** implement. Use a weekly table `{weekday: (open, close) | None}`. `next_opening` walks forward day by day, at most 14 days, otherwise raises `DomainError`. `make check` green. Commit `feat(policies): add store hours and StoreNow`.

### Task 4: local Postgres, migrations and runner

**Files:**
- Create: `docker-compose.yml` (repo root), `backend/migrations/001_extensions.sql`, `backend/migrations/002_policy_chunks.sql`, `backend/migrations/003_product_embeddings.sql`, `backend/src/emporio/db.py`, `backend/src/emporio/migrate.py`
- Modify: `Makefile`, `.github/workflows/ci.yml`, `.env.example` (comment the local URL)
- Test: `backend/tests/unit/test_db.py`, `backend/tests/integration/test_migrations.py` (marked `postgres`), `backend/tests/integration/conftest.py`

**Interfaces:**
- Produces:
  - `emporio.db.database_url() -> str`, which raises `DatabaseNotConfigured(DomainError)` with the message "DATABASE_URL is not set; run `make db` or see .env.example" when the variable is unset.
  - `emporio.db.connect(url: str | None = None) -> psycopg.Connection`, which calls `register_vector` when the `vector` type exists.
  - `emporio.migrate.apply_migrations(conn, directory: Path = MIGRATIONS_DIR) -> list[str]`, which returns the versions it applied.
  - `python -m emporio.migrate`.
  - Fixture `pg_conn` in `tests/integration/conftest.py`: it skips when `DATABASE_URL` is unset, runs the migrations, and truncates our tables after each test.
- **Schema:**
  - `001`: `CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS unaccent;`, plus the immutable wrapper `f_unaccent(text)`:
    `CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS $$ SELECT public.unaccent('public.unaccent', $1) $$;`
  - `002`: the `policy_chunks` columns are:
    - `section_id text PRIMARY KEY`;
    - `title text NOT NULL`;
    - `parent_title text`;
    - `body text NOT NULL`;
    - `embedding vector(384) NOT NULL`;
    - `tsv tsvector GENERATED ALWAYS AS (to_tsvector('portuguese', f_unaccent(coalesce(parent_title,'') || ' ' || title || ' ' || body))) STORED`.

    Plus an HNSW index (`vector_cosine_ops`) and a GIN index on `tsv`.
  - `003`: `product_embeddings(product_id integer PRIMARY KEY, embedding vector(384) NOT NULL)` + an HNSW cosine index.
  - The runner keeps `schema_migrations(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())` and applies the pending `NNN_*.sql` files in sorted order, one transaction each.
- **Compose:** service `db`, image `pgvector/pgvector:0.8.7-pg17`, port `5434:5432`, user/password/db `emporio`, named volume, `pg_isready` healthcheck.
- **Makefile targets:**
  - `db-up` runs `docker compose up -d --wait db`;
  - `migrate` runs `uv run python -m emporio.migrate`;
  - `db` runs `db-up` and `migrate`;
  - `test-pg` runs pytest with `-m postgres` and `DATABASE_URL` set to the local URL.
- **CI** (`backend-tests` job):
  - add a `services.postgres` container `pgvector/pgvector:0.8.7-pg17` with a health check;
  - set `env: DATABASE_URL: postgresql://emporio:emporio@localhost:5432/emporio`;
  - run `uv run pytest -q -m "not eval"`.

  `make check` locally stays offline.

- [ ] **Step 1: `build(db)` commit:** compose file, Makefile targets, CI service, `.env.example` comment.
- [ ] **Step 2: failing tests:**
  - `test_database_url_missing_raises_clear_error` (unit, monkeypatch env);
  - `test_apply_migrations_creates_tables_and_is_idempotent` (`postgres`): the first call returns `["001", "002", "003"]`, the second returns `[]`, and `policy_chunks` and `product_embeddings` exist;
  - `test_f_unaccent_strips_accents` (`postgres`): `SELECT f_unaccent('devolução')` returns `'devolucao'`.
- [ ] **Step 3:** run with `make db && make test-pg`, expect FAIL. Commit `test(db): migrations runner (red)`.
- [ ] **Step 4:** implement. `make check` (offline) and `make test-pg` are green. Commit `feat(db): add SQL migrations and runner`.

### Task 5: e5 embedder

**Files:**
- Create: `backend/src/emporio/embeddings.py`
- Test: `backend/tests/unit/test_embeddings.py`, `backend/tests/eval/test_e5_embedder.py` (marked `eval`), `backend/tests/fakes/hash_embedder.py`

**Interfaces:**
- Produces:
  - `TextEmbedder` Protocol: `embed_query(text: str) -> list[float]` and `embed_passages(texts: Sequence[str]) -> list[list[float]]`.
  - `E5Embedder(cache_dir: Path | None = None)`. It registers the custom model once with `TextEmbedding.add_custom_model(...)`, per research §2, and adds the prefixes `"query: "` and `"passage: "`.
  - `EMBEDDING_DIM = 384` and `EMBEDDING_MODEL = "intfloat/multilingual-e5-small"`.
  - Test helper `HashEmbedder`: a deterministic 384-dim unit vector from SHA-256 of the lowercased text, the same for query and passage. It is used by every `postgres` test.

- [ ] **Step 1: failing tests:**
  - `test_e5_adds_prefixes` (unit): inject a stub `TextEmbedding` whose `embed` records its inputs;
  - `test_hash_embedder_is_deterministic_unit_384`;
  - `eval`: `test_e5_real_vectors_are_384_unit_and_rank_related_text_higher`, where `"query: posso devolver?"` is closer to the passage for section 4.1 than to the one for 2.
- [ ] **Step 2:** run, expect FAIL. Commit `test(policies): e5 embedder contract (red)`. Scope `policies`, since it is the first consumer.
- [ ] **Step 3:** implement. `make check` is green; `uv run pytest -m eval tests/eval/test_e5_embedder.py` passes, downloading the model once. Commit `feat(policies): add e5 embedder`.

### Task 6: policies application (ports + use cases)

**Files:**
- Create: `backend/src/emporio/policies/application/ports.py`, `backend/src/emporio/policies/application/search_policies.py`, `backend/src/emporio/policies/application/ingest_policies.py`
- Test: `backend/tests/unit/policies/fakes.py`, `backend/tests/unit/policies/test_use_cases.py`

**Interfaces:**
- Consumes: `PolicyChunk` (Task 2).
- Produces:
  - `PolicyHit(chunk: PolicyChunk, score: float)`, frozen and slotted, in `policies/domain/policy_chunk.py`.
  - `PolicyIndex` Protocol with `search(question: str, k: int) -> Sequence[PolicyHit]` and `replace_all(chunks: Sequence[PolicyChunk]) -> None`.
  - `PolicySource` Protocol with `chunks() -> Sequence[PolicyChunk]`.
  - `SearchPolicies(index)`, with `__call__(question: str, k: int = 5) -> tuple[PolicyHit, ...]`. A blank question returns `()` without calling the index.
  - `IngestPolicies(source, index)`, with `__call__() -> int` (the number of chunks written). It raises `DomainError` when the source yields zero chunks.
  - Fake `InMemoryPolicyIndex` that ranks by keyword overlap.

- [ ] **Step 1: failing tests:**
  - `test_search_returns_top_k_hits`;
  - `test_blank_question_returns_empty_without_index_call`;
  - `test_ingest_replaces_all_and_returns_count`;
  - `test_ingest_refuses_empty_source`.
- [ ] **Step 2:** run, expect FAIL. Commit `test(policies): search and ingest use cases (red)`.
- [ ] **Step 3:** implement. `make check` green. Commit `feat(policies): add search and ingest use cases`.

### Task 7: Postgres hybrid policy index

**Files:**
- Create: `backend/src/emporio/policies/infrastructure/pg_policy_index.py`
- Test: `backend/tests/integration/test_pg_policy_index.py` (marked `postgres`)

**Interfaces:**
- Consumes: `TextEmbedder` (Task 5), `connect` (Task 4), `PolicyIndex` (Task 6).
- Produces: `PgPolicyIndex(conn: psycopg.Connection, embedder: TextEmbedder, *, hybrid: bool = True)`, which implements `PolicyIndex`.
- `replace_all`:
  - one transaction: `DELETE FROM policy_chunks`, then a batch `INSERT`;
  - passage embeddings come from `chunk.embedding_text`.
- `search`: one SQL statement with two ranked CTEs.
  - Vector side: `ORDER BY embedding <=> %(q)s LIMIT 20`.
  - Full-text side: `tsv @@ to_tsquery('portuguese', replace(plainto_tsquery('portuguese', f_unaccent(%(text)s))::text, ' & ', ' | '))`, ordered by `ts_rank` and limited to 20.
  - Fuse with `sum(1.0 / (60 + rank))` over a `FULL OUTER JOIN` on `section_id`, order by fused score, `LIMIT k`.
  - With `hybrid=False`, use only the vector side, with score `1 - distance`.
  - An empty `plainto_tsquery` (stopwords only) must not error; the full-text side then contributes nothing.

- [ ] **Step 1: failing tests** (`postgres`, `HashEmbedder`, chunks from Task 2's `read_policy_chunks()`):
  - `test_replace_all_is_idempotent`: two runs leave 25 rows;
  - `test_full_text_matches_without_accents`: with `hybrid=True`, `"devolucao"` puts a section containing "devolução" in the top 5, and `"domingo"` puts `2` in the top 5;
  - `test_vector_only_mode_returns_k_hits`;
  - `test_stopword_only_question_does_not_fail`: `"o que é"` returns ≤ 5 hits and does not raise.
- [ ] **Step 2:** run, expect FAIL. Commit `test(policies): hybrid pgvector index (red)`.
- [ ] **Step 3:** implement. `make check` and `make test-pg` are green. Commit `feat(policies): add hybrid Postgres policy index`.

### Task 8: `recommend_products` (catalog)

**Files:**
- Create: `backend/src/emporio/catalog/application/recommend_products.py`, `backend/src/emporio/catalog/infrastructure/pg_product_index.py`
- Modify: `backend/src/emporio/catalog/application/ports.py`
- Test: `backend/tests/unit/catalog/test_recommend_products.py`, `backend/tests/integration/test_pg_product_index.py` (marked `postgres`)

**Interfaces:**
- Consumes:
  - `CatalogRepository` (existing);
  - `Candidates`, `NoMatch` from `catalog/domain/search.py`;
  - `TextEmbedder`, `connect`.
- Produces:
  - `ProductIndex` Protocol: `similar(need: str, k: int) -> Sequence[int]` (product ids, best first) and `replace_all(products: Sequence[Product], category_names: Mapping[int, str]) -> None`.
  - `RecommendProducts(repo, index)`, with `__call__(need: str, limit: int = 5) -> Candidates | NoMatch`. It asks the index for 10, keeps only `is_available()` products in index order, and truncates to `limit`. A blank need, or no available product, returns `NoMatch`. It never returns `Exact`.
  - `PgProductIndex(conn, embedder)`. It embeds `f"{name}. {category}. {description}"` as a passage and uses vector search only.

- [ ] **Step 1: failing tests:**
  - unit with a fake index returning fixed ids:
    - `test_recommend_returns_candidates_in_index_order`;
    - `test_recommend_skips_unavailable_products` (a discontinued product, a `coming_soon` one and one with stock 0 are filtered out);
    - `test_recommend_never_returns_exact` (a single hit is still `Candidates`);
    - `test_blank_need_is_no_match`.
  - `postgres`: `test_product_index_replace_all_is_idempotent` (65 rows twice, using the real catalog via `CsvCatalogRepository`).
- [ ] **Step 2:** run, expect FAIL. Commit `test(catalog): semantic product recommendations (red)`.
- [ ] **Step 3:** implement. `make check` and `make test-pg` are green. Commit `feat(catalog): add recommend_products over pgvector`.

### Task 9: ingestion entry point and retrieval eval

**Files:**
- Create: `backend/src/emporio/ingest.py`, `backend/evals/policies_retrieval.toml`, `backend/tests/eval/test_policies_retrieval.py`
- Modify: `Makefile` (`ingest`, `evals`, and `db` now also runs `ingest`), `AGENTS.md` (commands: `make db`, `make test-pg`, `make evals`; gotcha: `DATABASE_URL` and the 470 MB model download on first use)

**Interfaces:**
- Consumes: Tasks 2 and 4–8.
- Produces:
  - `python -m emporio.ingest`, the composition root. It connects, applies migrations, ingests policies (`PdfPolicySource` wrapping `read_policy_chunks`, then `PgPolicyIndex`) and products (`CsvCatalogRepository`, then `PgProductIndex`) with `E5Embedder`. It prints `policies: 25, products: 65`.
  - `policies_retrieval.toml`: 20 `[[case]]` entries with `question` (pt-BR, as a customer would type it) and `expected` (section id). They are grounded in the PDF and must include:
    - "vocês abrem domingo?" → 2;
    - "o produto esgotou, e agora?" → 7.3;
    - "quero trocar a cor da guitarra" → 4.3;
    - "qual a garantia do instrumento?" → 8.1;
    - "posso devolver se me arrepender?" → 4.1;
    - "parcela em quantas vezes?" → 3.1.
  - The eval test (`eval` + `postgres`) ingests with `E5Embedder`. It prints hit@1, hit@3 and hit@5 for both `hybrid=False` and `hybrid=True`, and asserts hybrid hit@5 ≥ 0.9.

- [ ] **Step 1: failing test** `test_hybrid_retrieval_hit_at_5`, with the TOML. Commit `test(policies): retrieval eval over 20 questions (red)`.
- [ ] **Step 2:** implement `ingest.py` and the Makefile/AGENTS.md changes. Run `make db` (ingests); `make evals` passes. Paste the printed table into `docs/research/fase-3.md` § "Measured retrieval" (vector vs hybrid). Commit `feat(policies): add ingestion entry point and retrieval eval`.
- [ ] **Step 3:** if hybrid hit@5 < 0.9, stop and report the misses. Do not tune the questions to pass.

### Task 10: spec sync, PR and review
- [ ] **Step 1: spec sync** (`docs(spec): record phase 3 decisions`):
  - §7.2 policies: hybrid retrieval, store hours on the real clock, injected holidays.
  - §7.3 tools: `store_now` returns open + next opening; `recommend_products` is Candidates only.
  - §7.7 tree: add `emporio/embeddings.py`, `db.py`, `migrate.py`, `ingest.py`, `backend/migrations/`, `docker-compose.yml`, `backend/evals/policies_retrieval.toml`.
  - Data quirks: two WhatsApp numbers (3341-4444 quoted), the accented e-mail in 1.2, and the Campo Grande holiday marked unconfirmed.
- [ ] **Step 2:** `git push -u origin feat/policies-rag`, then `gh pr create`. The body is in English and ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 3:** run the `reviewing-changes` skill on the PR. Apply the FIX-NOW items.
- [ ] **Step 4:** checkpoint with the owner before merging. Show the measured vector-vs-hybrid table, and ask before touching the Railway service (phase 6 creates it).
