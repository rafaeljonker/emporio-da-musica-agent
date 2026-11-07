# Catalog in Postgres with hybrid search: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the agent reads products, categories and promotions from Postgres through one hybrid query (FTS + `pg_trgm` + pgvector, RRF k = 60), the pure domain grader keeps deciding Exact/Candidates/NoMatch, and any logged-in demo user can add a product in a "Catálogo" dialog and ask the agent about it on the next turn.

**Architecture:**
- **One `products` table** holds facts (price, stock, status) and search fields (`search_doc`, generated `tsv`, `name_key`, `code_key`, `embedding`). `CsvCatalogRepository` stays only as the seed source; `make ingest` upserts seed rows, embeds only rows whose document hash changed, and deletes every `source='admin'` row (the manual reset).
- **Reads:** `PgCatalogRepository` (catalog infrastructure owns all SQL) implements the new `CatalogRepository` port: `get`, `get_many`, `categories`, `promotions_for`, `promoted`, `search`. `SearchProducts` asks `search` for a pool of 40 and runs the existing grader over it; `RecommendProducts` is `search` with `available_only=True`. Tool JSON is unchanged.
- **Writes (a separate actor, not the agent):** `CreateProduct`/`UpdateProduct` use cases over a `CatalogWriter` port; `PgCatalogWriter` embeds synchronously (NULL plus a log line on failure) and writes the row and an audit row in one transaction. The API reaches them only through a `CatalogAdmin` port in `support.application`, implemented in `support.infrastructure`. No agent tool and no MCP tool writes.

**Tech stack:** PostgreSQL 17 local / 18 on Railway, pgvector 0.8.x (`hnsw.iterative_scan`), `pg_trgm` 1.6, psycopg 3, fastembed e5-small, FastAPI + Pydantic v2, React 19 + radix-ui `Dialog` (already a dependency through `radix-ui`), Vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-05-emporio-agent-design.md` §3, §4, §7.1–7.2, §7.3.1. **Research + owner decisions (binding):** `docs/research/catalog-db.md`, including §8 (schema and SQL sketch) and "Owner decisions" (2026-11-07).

## Global Constraints
- **Branch and commits:** branch `feat/catalog-db` (already checked out; do not switch). TDD pairs: `test(<scope>): … (red)` then `feat(<scope>): …`; scopes `catalog`, `support`, `api`, `web`, `e2e`, `evals`, `docs`. Scaffolding goes in `chore`/`build` commits, never in a red commit. Subject ≤ 72 chars, imperative. Every commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Run `export PATH="$PWD/backend/.venv/bin:$PATH"` before committing. Never `--no-verify`, never amend, never force-push, never `# noqa`.
- **Gates:**
  - `make check` is green on every non-red commit and stays DB-free: use cases are tested through ports with `FakeCatalogRepository` / fake writers; SQL is tested only under `@pytest.mark.postgres`.
  - `make check-web` is green on every commit that touches `frontend/`.
  - `make test-pg`, `make e2e` and `make evals PROVIDER=gemini` are green before the PR. Evals: ≥ 90% of the 22 golden cases and 0 AI tells, plus the new product retrieval hit@5 ≥ 0.9. **If a golden case drifts, stop and report to the owner** with the failing transcript; do not tune prompts or the grader to pass.
- **Contracts that must not move:** the JSON of `search_products`, `get_product`, `recommend_products` and `list_active_promotions` (`serializers.py` is not edited); the strict tool schemas; MCP parity (`tests/contract/` unchanged and green). The agent and MCP stay read-only.
- **Layering (`make imports`):** SQL lives only in `catalog/infrastructure/`. `api/` imports only `support.application`, `support.domain`, `shared`, `config`. `support.application` never imports `catalog.domain`, so the admin DTOs there use primitives and `Decimal`.
- **Migrations:** numbered after 005 (`006_catalog.sql`, `007_drop_product_embeddings.sql`), written with `IF NOT EXISTS` / `IF EXISTS` so a re-run is harmless.
- **Owner decisions (2026-11-07, binding):** FTS + `pg_trgm` + pgvector, RRF k = 60, one SQL statement; keep the domain grader; availability and price ceiling filtered in SQL with `SET LOCAL hnsw.iterative_scan = relaxed_order` and `SET LOCAL hnsw.ef_search = 100` (this supersedes the phase 3 "never filter in the vector SQL" rule); synchronous embed on write, NULL on failure and logged; any logged-in demo user may create; create and edit own rows only, seed rows read-only, no delete, one product per request, no CSV upload; reset is manual `make ingest`; `product_embeddings` is dropped in this PR; the README cites the research probe numbers and no benchmark script is committed.
- **Write protection:** strict Pydantic body (`extra="forbid"`, stripped and bounded strings, `price` a decimal string turned into `Decimal`, never a float), DB `CHECK`s, 10 writes per minute per login (`lid`, scaled by `RATE_LIMIT_MULTIPLIER`), at most 20 rows per login and 500 admin rows overall.
- **Data:** `data/` is read-only; the CSVs only seed.
- **Hosted demo** (Gemini on Modal + Railway Postgres): re-ingest and redeploy are **[ASK]** steps: tell the owner the cost (CPU only, cents) and run them only after a yes.
- **Secrets and hygiene:** never print or commit secrets or URLs with credentials; no personal names, other projects, workspace names, `*.modal.run` URLs or local absolute paths in committed files. English code and docs; pt-BR `README.md` and UI copy.
- **Frontend:** pt-BR copy in `frontend/src/copy.ts`, shadcn components and existing tokens only (no new colours, no new dependency, no router). Every field has a `<Label>`, errors are tied with `aria-describedby` and `aria-invalid`, a form-level failure is `role="alert"`, and the dialog traps focus and returns it to its trigger.
- **README:** stays clean (owner requirement): one short section plus links, and only the lines this change makes false are corrected.
- **Time:** about 4.5 h. Cut order if late, from the last frontend step backwards: (1) editing own products in the UI (the API keeps `PUT`), (2) the "Seus produtos" list. Never cut the backend switch, the evals or the spec sync.

## Review Focus
1. **Editing someone else's row or a seed row** (`PUT` on id 95, or on a row created by another login). Expected: `404 not_found`, the row is unchanged, and the response never tells "exists but not yours" apart from "missing". Tests: Task 5 `test_update_ignores_seed_and_foreign_rows`, Task 6 `test_put_foreign_or_seed_product_is_404`.
2. **The embedder failing on a write** (model not loaded, OOM). Expected: the product is saved with `embedding NULL`, a warning is logged, and the next text search finds it by name. Test: Task 5 `test_create_with_failing_embedder_saves_and_is_searchable`.
3. **A category query bigger than a small pool** ("violões até 1000": 35 violões, the grader then sorts by price). Expected: every available violão under the ceiling reaches the grader, as with the CSV. Tests: Task 2 `test_search_passes_named_category_and_ceiling`, Task 3 `test_category_filter_returns_whole_category`.
4. **Price ceiling exactly at a promotional price.** Expected: SQL and `quote_price` agree to the cent (`round(price * (100 - percent) / 100, 2)`, half up like `Money.percent_off`): a ceiling equal to the final price includes the product, one cent less excludes it, and a raw price that rounds down to the ceiling is included. Tests: Task 3 `test_max_price_uses_promotional_final_price`, `test_max_price_rounds_the_final_price_like_money`.
5. **Hostile or sloppy create bodies:** extra keys (`id`, `source`, `owner`), a whitespace-only name, `price` as `"1e3"`, `"0"`, `"0.001"`, a JSON float or `true`, negative stock, 21 spec keys, a 2001-char description, an unknown category. Expected: `422` (unknown category: `422 unknown_category`), nothing written. Tests: Task 6 `test_create_rejects_invalid_bodies` (parametrized) and `test_create_unknown_category_is_422`.

---

### Task 1: catalog schema (migration 006) — ~20 min

**Files:**
- Create: `backend/migrations/006_catalog.sql`
- Modify: `backend/tests/conftest.py` (`pg_conn` teardown truncates `promotions, products, categories, catalog_audit` too, with `RESTART IDENTITY CASCADE`)
- Test: `backend/tests/integration/test_migrations.py`

**Interfaces:**
- Produces the research §8 schema verbatim, with these additions:
  - `CREATE EXTENSION IF NOT EXISTS pg_trgm;` first.
  - `products.owner text` with `CHECK ((source = 'seed') = (owner IS NULL))`; `owner` is the creating login's `lid`.
  - `CREATE SEQUENCE IF NOT EXISTS products_admin_id_seq START 100000;` (seed rows keep their CSV ids).
  - `specs jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(specs) = 'object')`.
  - `catalog_audit` as in §8, no FK (an audit row survives the reset).
  - Every `CREATE TABLE/INDEX` uses `IF NOT EXISTS`.

- [ ] **Step 1: failing tests** in `test_migrations.py`:
  - `test_catalog_tables_exist_with_trgm`: after `apply_migrations`, `pg_extension` has `pg_trgm`, and `products`, `categories`, `promotions`, `catalog_audit` exist.
  - `test_products_generated_search_columns`: insert one category and a product named `"Violão Takamine GD-20 NS"` (`search_doc` any text). `name_key` is `violao takamine gd-20 ns`, the code column is that text with every non-alphanumeric character removed (`violao` + `takamine` + `gd20ns`, glued), and `tsv @@ plainto_tsquery('portuguese', 'takamine')`.
  - `test_products_checks_reject_bad_rows`: `price = 0`, `stock = -1`, `status = 'sold'`, and `source = 'admin'` with a NULL `owner` each raise `psycopg.errors.CheckViolation`.
- [ ] **Step 2:** `make test-pg` → those fail. Red commit `test(catalog): catalog tables migrate (red)`. Write the migration, `make test-pg` and `make check` green, commit `feat(catalog): add the catalog schema with trigram and HNSW indexes`.

### Task 2: read port, fake and use cases over `search` (DB-free) — ~50 min

**Files:**
- Modify: `backend/src/emporio/catalog/application/ports.py`, `get_product.py`, `list_promotions.py`, `search_products.py`, `recommend_products.py`; `backend/src/emporio/catalog/domain/search.py` (one public function); `backend/src/emporio/support/infrastructure/agent/tools.py` (helpers only); `backend/tests/unit/catalog/fakes.py`
- Test: `backend/tests/unit/catalog/test_use_cases.py`, `test_recommend_products.py`, `test_search.py`, `backend/tests/unit/support/test_tools.py`

**Interfaces:**
- In `catalog/application/ports.py` (replaces `products()`, `promotions()` and the `ProductIndex` port):
  ```python
  @dataclass(frozen=True, slots=True)
  class CatalogFilter:
      category_ids: frozenset[int] | None = None
      available_only: bool = False
      max_price: Money | None = None  # the final price after the best active promotion

  class CatalogRepository(Protocol):
      def get(self, product_id: int) -> Product | None: ...
      def get_many(self, ids: Collection[int]) -> Sequence[Product]: ...  # any order; unknown ids skipped
      def categories(self) -> Sequence[Category]: ...
      def promotions_for(self, ids: Collection[int]) -> Sequence[Promotion]: ...  # active and inactive
      def promoted(self) -> Sequence[Product]: ...  # available products with an active promotion
      def search(self, query: str, flt: CatalogFilter, k: int) -> Sequence[Product]: ...  # best first
  ```
- `catalog/domain/search.py`: `named_categories(categories: Sequence[Category], query: str) -> frozenset[int]`, the ids whose name tokens contain a query word (same `_query_words` and `tokens` normalisation as the grader, no typo path because that path needs the product pool).
- `SearchProducts.__call__(query, max_price=None, include_unavailable=False)` keeps its signature. It calls `repo.search(query, CatalogFilter(named_categories(...) or None, False, max_price), POOL)` with `POOL = 40`, then `search_products(pool, repo.categories(), query, include_unavailable)`. Availability stays in the grader here, so a hidden exact hit is still reported with its status (the `descontinuado` case). No NoMatch fallback: `match: none` keeps its meaning.
- `GetProduct`: `repo.get` (else `ProductNotFound`) plus `best_active_promotion(repo.promotions_for([id]))`.
- `ListPromotions`: `repo.promoted()` plus one `promotions_for(ids)`; same output and order (by name).
- `RecommendProducts(repo: CatalogRepository)` (the index argument goes away): `repo.search(need, CatalogFilter(available_only=True), limit)` → `Candidates` or `NoMatch`; blank need or `limit <= 0` → `NoMatch` without a call.
- `tools.py`: `_quotes(box, products)` makes one `promotions_for` call; `_categories(box, products)` maps from `categories()` and each product's `category_id`; `_product_names(box, orders)` uses `get_many` of the order items' ids. No helper iterates the catalog any more.
- `FakeCatalogRepository(products, categories, promotions)`: implements the port in memory. Its `search` ignores `query` and `k` and returns every product passing the filter (price via `quote_price`), so the grader does the work as today. It records each `(query, flt, k)` in `searches` for spy assertions.

- [ ] **Step 1: failing tests:**
  - `test_named_categories_matches_plural_and_accent`: with category `(5, "Violões")`, `"violões até 1000"` and `"violao"` → `frozenset({5})`; `"takamine gd20"` → `frozenset()`.
  - `test_search_passes_named_category_and_ceiling`: `SearchProducts(fake)("violões até 1000", Money(Decimal(1000)))` records `CatalogFilter(frozenset({5}), False, Money(Decimal(1000)))` and `k == 40`.
  - `test_recommend_asks_only_available_with_limit`: the recorded filter has `available_only=True` and `k == 3` for `limit=3`; an empty result → `NoMatch`.
  - The existing tests in `test_use_cases.py`, `test_recommend_products.py` and `test_tools.py`, ported to the new fake with their assertions unchanged (`FakeIndex` goes away; ranking-order tests for `recommend` now assert the fake's order).
- [ ] **Step 2:** red commit `test(catalog): use cases read through catalog search (red)`. Implement, then `make check` green. Until Task 4, `bootstrap.py` still wires `CsvCatalogRepository`. Give it the new port methods as a temporary in-memory shim that behaves like the fake (its `search` returns every product passing the filter, cut to `k`), and wire `RecommendProducts(catalog)`. `PgProductIndex` stays only for `ingest.py`. This keeps the app runnable; Task 4 deletes the shim. Commit `feat(catalog): read the catalog through a search port`.

### Task 3: `PgCatalogRepository` hybrid search and the seed — ~60 min

**Files:**
- Create: `backend/src/emporio/catalog/infrastructure/pg_catalog_repository.py`, `backend/src/emporio/catalog/infrastructure/pg_catalog_writer.py` (seed only here; Task 5 adds writes)
- Modify: `backend/src/emporio/catalog/domain/product.py` (`search_document`), `backend/tests/conftest.py` (fixture `catalog_repo`)
- Test: `backend/tests/integration/test_pg_catalog.py`, `backend/tests/unit/catalog/test_product.py`

**Interfaces:**
- `search_document(name: str, category: str, description: str, specs: Sequence[tuple[str, str]]) -> str` = `f"{name}. {category}. {description} {'; '.join(f'{k}: {v}' for k, v in specs)}"`, stripped.
- `PgCatalogRepository(pool: ConnectionPool, embedder: TextEmbedder)` implements the Task 2 port.
  - `search`: the research §8 statement, with `{flt}` built once in Python and inlined in all three branches. The filter params are `cats int[] | None`, `available bool`, `max_price numeric | None`. The price predicate is `p.price * (100 - coalesce((SELECT max(x.percent) FROM promotions x WHERE x.product_id = p.id AND x.active), 0)) / 100 <= %(max_price)s`. Drop the `LEFT JOIN LATERAL` promotion (the tools read promotions through `promotions_for`). It runs inside `conn.transaction()` after `SET LOCAL hnsw.iterative_scan = relaxed_order` and `SET LOCAL hnsw.ef_search = 100`. A blank query returns `[]` without embedding.
  - `categories()` is loaded once per instance (9 rows; category edits are out of scope).
  - `specs` come back as `tuple(row_specs.items())`. `psycopg.OperationalError`/`PoolTimeout` → `IndexUnavailable`, as in `pg_policy_index.py`.
- `PgCatalogWriter(pool: ConnectionPool, embedder: TextEmbedder)`:
  - `seed(categories: Sequence[Category], products: Sequence[Product], promotions: Sequence[Promotion]) -> int` returns how many products it embedded.
  - In one transaction: `DELETE` promotions, then admin products; upsert categories; upsert products with `source='seed'` (`ON CONFLICT (id) DO UPDATE`); re-insert promotions.
  - It embeds only rows whose `sha256(search_doc)` differs from the stored `embedded_hash`, in one `embed_passages` batch done before the transaction.
- `tests/conftest.py`: fixture `catalog_repo(pg_pool) -> PgCatalogRepository`, seeded from `CsvCatalogRepository()` with `HashEmbedder`.

- [ ] **Step 1: failing tests** (`test_pg_catalog.py`, `pytestmark = pytest.mark.postgres`; `test_product.py` for the document):
  - `test_search_document_joins_fields`: `("Yamaha C40", "Violões", "Nylon.", (("cordas", "nylon"),))` → `"Yamaha C40. Violões. Nylon. cordas: nylon"`.
  - `test_seed_is_idempotent_and_embeds_once`: two seeds → 65 products, 9 categories, 24 promotions; the first returns 65, the second 0.
  - `test_seed_removes_admin_rows`: an admin row inserted by SQL (id 100000, `owner 'x'`) is gone after `seed`.
  - `test_get_many_and_get`: `get(95).name` contains `GD20`; `get(999999) is None`; `{p.id for p in get_many([95, 81, 999999])} == {95, 81}`.
  - `test_search_finds_codes_and_typos`: each of `("takamine gd 20", 95)`, `("SN-7C", 113)`, `("telecastr", 134)`, `("yamah c70", 82)` has its id in the top 3 of `search(q, CatalogFilter(), 10)`.
  - `test_available_only_excludes_unavailable`: no id from `{113, 130, 136, 96}` in `search("violão", CatalogFilter(available_only=True), 40)`.
  - `test_max_price_uses_promotional_final_price`: for the first CSV product with an active promotion, `final = quote_price(p, best).final.amount`; its name searched with `max_price=Money(final)` includes it, and with `Money(final - Decimal("0.01"))` excludes it.
  - `test_category_filter_returns_whole_category`: with `CatalogFilter(category_ids=frozenset({5}))` (Violões) and `k=40`, `search("violões", ...)` returns exactly the CSV's 35 violões.
  - `test_row_without_embedding_is_found_by_text`: `UPDATE products SET embedding = NULL WHERE id = 95`; `search("takamine gd20", CatalogFilter(), 5)` still contains 95.
  - `test_promoted_matches_csv`: ids of `promoted()` equal the CSV products that are available and have an active promotion.
- [ ] **Step 2:** red commit `test(catalog): hybrid catalog search in Postgres (red)`. Implement, `make test-pg` and `make check` green. Commit `feat(catalog): hybrid FTS, trigram and vector product search`.

### Task 4: switch the agent to Postgres, drop `product_embeddings`, retrieval eval — ~40 min + eval run

**Files:**
- Create: `backend/migrations/007_drop_product_embeddings.sql` (`DROP TABLE IF EXISTS product_embeddings;`), `backend/evals/products_retrieval.toml`, `backend/tests/eval/test_products_retrieval.py`
- Delete: `backend/src/emporio/catalog/infrastructure/pg_product_index.py`, `backend/tests/integration/test_pg_product_index.py`, the Task 2 shim methods on `CsvCatalogRepository`
- Modify: `backend/src/emporio/bootstrap.py`, `backend/src/emporio/ingest.py`, `backend/tests/conftest.py` (drop `product_embeddings` from the truncate), `backend/tests/unit/test_bootstrap.py`, `backend/tests/integration/{test_pool,test_fresh_database,test_migrations}.py`, `backend/tests/eval/test_agent_evals.py`
- Test: `backend/tests/integration/test_fresh_database.py`

**Interfaces:**
- `build_toolbox(stack, url, settings) -> tuple[Toolbox, CsvCustomerRepository, ConnectionPool, TextEmbedder]`, with `catalog = PgCatalogRepository(pool, embedder)` and `RecommendProducts(catalog)`. Task 6 reuses the embedder for the writer, so the e5 model loads once.
- `ingest.main` prints `policies: N, products: 65 (embedded M)`, using `PgCatalogWriter(pool, embedder).seed(csv.categories(), csv.products(), csv.promotions())`.
- `test_agent_evals.py` seeds with `PgCatalogWriter(...).seed` and `_derive_facts` builds the use cases over `PgCatalogRepository`; raw lists (`gd20`, `c40`, the discontinued product, the Takamines) keep coming from `CsvCatalogRepository`, which is the seed.
- `products_retrieval.toml`: the research's 30 labelled cases, `[[case]] group/query/expected = [ids]`; `U` = ids 116–130.
  - code: `Yamaha C40` [81]; `quanto custa o takamine gd20` [95]; `takamine gd 20` [95]; `SN-7C` [113]; `fg800` [92]; `martin d28` [93, 108]; `kala ka-15s` [116]; `apx600` [104]; `fender telecaster` [134]; `les paul` [131]; `gc5ce` [100].
  - typo: `yamah c70` [82]; `takamine gd2o` [95]; `telecastr` [134]; `stratocastr` [145]; `ukelele kala soprano` [116]; `violao giannini gnf3` [101]; `ibanes rg550` [132].
  - meaning: `violão de nylon para iniciante` [81, 83, 84, 85]; `instrumento pequeno de quatro cordas pra levar em viagem` U; `violão de 7 cordas para choro` [109–113]; `bateria para gravar em estúdio` [139, 140, 141]; `sintetizador para produzir música eletrônica` [142, 143, 144]; `contrabaixo de 5 cordas` [137]; `violão folk com captação para tocar ao vivo` [94, 103–108]; `ukulele com som mais grave` [124, 128, 129, 130]; `guitarra para rock pesado com ponte tremolo` [132]; `violão com afinador embutido` [86, 99, 107]; `piano de palco` [143]; `violão eletroacústico de nylon` [98–102, 115].
- `test_products_retrieval.py` (`eval` + `postgres`, real `E5Embedder`): seeds, runs `search(q, CatalogFilter(), 5)`, prints hit@1/hit@5 per group, asserts overall hit@5 ≥ 0.9 (research: 0.97).

- [ ] **Step 1: failing test:** `test_fresh_database_ingest_seeds_catalog`: on an empty `_test` database, `ingest.main()` leaves 65 products with non-NULL embeddings (HashEmbedder through the existing monkeypatch pattern in that file), and `to_regclass('product_embeddings') IS NULL`. Red commit `test(catalog): ingest seeds the Postgres catalog (red)`.
- [ ] **Step 2:** wire, delete, write the migration and the eval files. Run `make check`, `make test-pg` and `make e2e`. Commit `feat(catalog): serve the agent from the Postgres catalog`.
- [ ] **Step 3:** `make evals PROVIDER=gemini`. Expected: policies hit@5 ≥ 0.9, products hit@5 ≥ 0.9, golden cases ≥ 90% with 0 AI tells. Watch `catalogo_violoes`, `preco_takamine`, `takamine_ambiguo`, `descontinuado`, `recomendacao_mpb` and `promocoes`. **If any case that passed in the last committed `backend/evals/reports/gemini.md` now fails, stop and report to the owner.** On green, `git add -f backend/evals/reports/gemini.md` and commit `docs(evals): Gemini rerun on the Postgres catalog`.

### Task 5: write path — drafts, use cases, `PgCatalogWriter` — ~40 min

**Files:**
- Create: `backend/src/emporio/catalog/application/create_product.py`, `update_product.py`
- Modify: `backend/src/emporio/catalog/domain/product.py` (`ProductDraft`), `catalog/domain/errors.py`, `catalog/application/ports.py` (`CatalogWriter`), `catalog/infrastructure/pg_catalog_writer.py`, `backend/tests/unit/catalog/fakes.py` (`FakeCatalogWriter`)
- Test: `backend/tests/unit/catalog/test_write_use_cases.py`, `backend/tests/integration/test_pg_catalog_writer.py`

**Interfaces:**
- `ProductDraft`: a frozen dataclass with `Product`'s fields minus `id` (`name, category_id, description, price: Money, stock, status: ProductStatus, specs`). Bounds are enforced at the edge (Task 6) and by the DB `CHECK`s, not repeated here.
- `catalog/domain/errors.py`: `UnknownCategory(category_id)`, `ProductNotOwned(product_id)` (also used for missing and seed rows), `CatalogFull()`, all `DomainError`.
- Port:
  ```python
  class CatalogWriter(Protocol):
      def create(self, owner: str, draft: ProductDraft) -> Product: ...
      def update(self, owner: str, product_id: int, draft: ProductDraft) -> Product | None: ...  # None: missing, seed or foreign
      def own(self, owner: str) -> Sequence[Product]: ...
      def admin_total(self) -> int: ...
  ```
- `CreateProduct(repo: CatalogRepository, writer: CatalogWriter, max_per_owner: int = 20, max_total: int = 500)`, called as `(owner, draft) -> Product`:
  - an unknown `category_id` raises `UnknownCategory`;
  - `len(writer.own(owner)) >= max_per_owner` or `writer.admin_total() >= max_total` raises `CatalogFull`.
  - Mark it `# ponytail: caps are checked then written without a lock; two racing creates can pass one over the cap, fine for a demo`.
- `UpdateProduct(repo, writer)`, called as `(owner, product_id, draft) -> Product`: `UnknownCategory` as above; a `None` from the writer raises `ProductNotOwned`.
- `PgCatalogWriter.create`/`update`:
  - Build `search_document` with the category name. Embed before the transaction; on any exception, `logger.warning("product embed failed: %s", type(err).__name__)` and store NULL.
  - Insert with `nextval('products_admin_id_seq')`, `source='admin'`, `owner`, `embedded_hash`. `update` uses `WHERE id = %s AND source = 'admin' AND owner = %s RETURNING …`, and re-embeds only when the hash changed.
  - Write `catalog_audit(actor=owner, action='create'|'update', product_id, after=<row as jsonb, price as text>)` in the same transaction.

- [ ] **Step 1: failing tests:**
  - Unit (fakes): `test_create_rejects_unknown_category`; `test_create_stops_at_owner_cap` (20 own rows → `CatalogFull`); `test_create_stops_at_total_cap`; `test_update_missing_or_foreign_is_not_owned`.
  - Postgres (seeded `catalog_repo`, `HashEmbedder`):
    - `test_created_product_is_found_by_next_search`: create "Cavaquinho Rozini Choro Profissional RC-77X" and it is in the top 3 of `search("cavaquinho rozini", CatalogFilter(available_only=True), 10)`; its id is ≥ 100000; one audit row with action `create`.
    - `test_create_with_failing_embedder_saves_and_is_searchable`: the embedder raises `RuntimeError`; the row has `embedding IS NULL`, `caplog` has the warning, and `search("rozini", …)` finds it.
    - `test_update_ignores_seed_and_foreign_rows`: `update("a", 95, draft)` and `update("b", <row of a>, draft)` return `None`, and neither row changed.
    - `test_price_only_update_keeps_embedding`: a counting embedder is called 0 times on an update that changes only price and stock.
- [ ] **Step 2:** red commit `test(catalog): create and edit own products (red)`. Implement, `make check` and `make test-pg` green. Commit `feat(catalog): create and edit own products with sync embedding`.

### Task 6: catalog admin API — ~35 min

**Files:**
- Create: `backend/src/emporio/api/catalog.py`, `backend/src/emporio/support/infrastructure/catalog_admin.py`, `backend/tests/fakes/fake_catalog_admin.py`
- Modify: `backend/src/emporio/support/application/ports.py`, `backend/src/emporio/api/app.py` (`create_app(agent, warmup, settings, catalog, *, static_dir=None)`), `backend/src/emporio/web.py`, `backend/src/emporio/bootstrap.py` (`Agent.catalog_admin: CatalogAdmin`, a required field placed after `customer_exists`), `backend/tests/unit/api/conftest.py`
- Test: `backend/tests/unit/api/test_catalog.py`, `backend/tests/unit/test_bootstrap.py`

**Interfaces:**
- `support/application/ports.py` (primitives only):
  ```python
  @dataclass(frozen=True)
  class ProductInput:
      name: str; category_id: int; description: str; price: Decimal; stock: int; status: str
      specs: tuple[tuple[str, str], ...]

  @dataclass(frozen=True)
  class ProductView:
      id: int; name: str; category_id: int; category: str; description: str; price: Decimal
      stock: int; status: str; specs: tuple[tuple[str, str], ...]

  class CatalogWriteRejected(DomainError):
      def __init__(self, code: Literal["unknown_category", "not_found", "catalog_full"]) -> None: ...

  class CatalogAdmin(Protocol):
      def categories(self) -> tuple[tuple[int, str], ...]: ...
      def create(self, owner: str, data: ProductInput) -> ProductView: ...
      def update(self, owner: str, product_id: int, data: ProductInput) -> ProductView: ...
      def mine(self, owner: str) -> tuple[ProductView, ...]: ...  # newest first
  ```
- `support/infrastructure/catalog_admin.py`: `CatalogAdminService(repo, writer, create: CreateProduct, update: UpdateProduct)` maps DTOs to and from `ProductDraft`/`Product`, and maps `UnknownCategory`/`ProductNotOwned`/`CatalogFull` to `CatalogWriteRejected`. `bootstrap.build_agent` builds it with `PgCatalogWriter(pool, embedder)` from `build_toolbox`'s embedder. `build_mcp` gets no writer.
- `api/catalog.py`: `build_catalog_router(catalog: CatalogAdmin, settings: Settings) -> APIRouter`, prefix `/api/catalog`. Every route needs the session, and the owner is `request.session["lid"]` (missing → 401). Writes go through `require_json` and `SlidingWindow(10 * settings.rate_limit_multiplier, 60)` keyed by `lid` (429 `too_many_writes`).
  - `ProductIn` uses `ConfigDict(extra="forbid", str_strip_whitespace=True)`:
    - `name` 2–120;
    - `category_id: StrictInt` ≥ 1;
    - `description` 0–2000;
    - `price: str` matching `^\d{1,6}(\.\d{1,2})?$`, converted to `Decimal`, and `> 0`;
    - `stock: StrictInt` 0–100000;
    - `status: Literal["active", "discontinued", "coming_soon"]`;
    - `specs: dict[str, str]`, at most 20 entries, each key 1–40 and each value 1–120 characters (stripped).
  - Response product JSON: `{id, name, category_id, category, description, specs: {k: v}, price: "1234.50", stock, status}`, with `price` as a decimal string like `cost_brl`.
  - `GET /categories` → `200 [{"id", "name"}]`. `GET /products/mine` → `200 [product]`. `POST /products` → `201 product`. `PUT /products/{product_id}` (path `int` ≥ 1) → `200 product`. `CatalogWriteRejected` maps `unknown_category` → 422, `not_found` → 404, `catalog_full` → 409, each as `{"detail": code}`.

- [ ] **Step 1: failing tests** (`FakeCatalogAdmin` records calls and can be told to raise):
  - `test_catalog_routes_need_session` (each of the four → 401);
  - `test_create_returns_201_with_decimal_string_price` (`"1234.5"` → `"1234.50"`, owner = the session's `lid`);
  - `test_create_rejects_invalid_bodies`, parametrized over Review Focus 5's bodies → 422 and the fake saw no call;
  - `test_create_requires_json` (415);
  - `test_create_unknown_category_is_422`;
  - `test_put_foreign_or_seed_product_is_404`;
  - `test_catalog_full_is_409`;
  - `test_eleventh_write_in_a_minute_is_429`;
  - `test_mine_is_scoped_to_login` (two logins see only their own calls);
  - `test_build_agent_wires_catalog_admin` in `test_bootstrap.py`.
- [ ] **Step 2:** red commit `test(api): catalog admin routes (red)`. Implement, `make check` green. Commit `feat(api): let demo users create and edit their own products`.

### Task 7: "Catálogo" dialog in the web demo — ~45 min

**Files:**
- Create: `frontend/src/components/ui/dialog.tsx` (shadcn's Dialog over `radix-ui`, no new dependency), `frontend/src/catalog/form.ts`, `frontend/src/catalog/form.test.ts`, `frontend/src/catalog/CatalogDialog.tsx`
- Modify: `frontend/src/api/client.ts`, `frontend/src/api/types.ts`, `frontend/src/copy.ts`, `frontend/src/chat/ChatShell.tsx` (a `CatalogDialog` beside `MetricsDetails` inside `DemoStrip`; `onAsk` sets the composer text and focuses `composer-input`)
- Test: `frontend/src/catalog/form.test.ts`, `e2e/test_demo_flow.py`

**Interfaces:**
- `client.ts`: `catalogCategories()`, `myProducts()`, `createProduct(body: ProductBody)`, `updateProduct(id: number, body: ProductBody)`. A 422 throws `HttpError` with the `detail`, and a 401 throws `SessionExpired`, both through the existing `call`.
- `form.ts`, pure:
  - `toPrice(text: string): string | null` parses pt-BR and dot input into `"1234.50"`, or `null` when invalid or ≤ 0.
  - `parseSpecs(text: string): Record<string, string> | null` reads one `Chave: valor` per line, ignores blank lines, and returns `null` past 20 lines or when a line has no colon.
  - `validate(fields: ProductFields): { body?: ProductBody; errors: Partial<Record<keyof ProductFields, string>> }`, with the server's bounds and messages from `copy.catalog.errors`.
- `CatalogDialog({ onAsk, onSessionExpired })`:
  - The trigger is a ghost `Button` "Catálogo" (lucide `PackagePlus`, `aria-hidden` icon) styled like the Métricas toggle.
  - The radix `Dialog` has `DialogTitle` "Cadastrar produto" and a description; it is full height below `md` and `max-w-lg` from `md`.
  - The form: Nome (`Input`), Categoria (`Select` from `/categories`), Descrição (`Textarea`), Preço (R$) (`Input inputMode="decimal"`), Estoque (`Input type="number" min=0`), Situação (`Select`: Ativo / Descontinuado / Em breve), Especificações (`Textarea`, placeholder `Cordas: nylon`).
  - Each error sits in a `<p id=…>` referenced by `aria-describedby`. On submit, focus goes to the first invalid field. A server or network failure shows a `role="alert"` line.
  - Success state (replaces the form; focus on its heading): "Produto cadastrado." plus a "Perguntar ao assistente" button, which calls `onAsk(copy.catalog.askPrompt(name))` and closes the dialog, plus "Cadastrar outro".
  - Cut 2: "Seus produtos" lists `/products/mine`. Cut 1: an "Editar" button on each row reopens the form filled in and sends `PUT`.
- `copy.catalog` (pt-BR):
  - `trigger: 'Catálogo'`, `title: 'Cadastrar produto'`;
  - `description: 'Produtos que você cadastrar aqui entram na busca do assistente na hora. Os produtos da loja não podem ser alterados.'`;
  - `submit: 'Cadastrar'`, `saving: 'Salvando…'`, `saved: 'Produto cadastrado.'`;
  - `ask: 'Perguntar ao assistente'`, `askPrompt: (name) => \`Vocês têm o ${name}?\``, `another: 'Cadastrar outro'`;
  - `mine: 'Seus produtos'`, `edit: 'Editar'`;
  - `failed: 'Não deu pra salvar agora. Tenta de novo em instantes.'`, `tooMany: 'Muitos cadastros seguidos. Espera um minuto.'`, `full: 'Você chegou ao limite de produtos desta demonstração.'`;
  - `errors`: name, price, stock, category and specs messages, each one short sentence.

- [ ] **Step 1: failing Vitest** (`form.test.ts`):
  - `toPrice`: `"1.234,50"` and `"1234.5"` give `"1234.50"`, `"0"` gives `null`, `"abc"` gives `null`, `"0,001"` gives `null`;
  - `parseSpecs`: two lines give two keys; 21 lines give `null`; a line without a colon gives `null`;
  - `validate`: an empty name gives `errors.name`; a valid set gives a `body` whose `price` is a string.
  Red commit `test(web): catalog form parsing and validation (red)`.
- [ ] **Step 2:** implement `form.ts`, the dialog, the client and the copy. `make check-web` green. Commit `feat(web): add the Catálogo dialog to the demo strip`.
- [ ] **Step 3: e2e** `test_catalog_create_then_ask` (scripted model):
  - sign in, click "Catálogo", fill a unique name `f"Cavaquinho Teste {uuid4().hex[:6]}"`, category "Violões" (there is no cavaquinho category), price `899,90`, stock `3`, and submit;
  - expect the "Produto cadastrado." heading, click "Perguntar ao assistente";
  - expect the dialog closed and `#composer-input` to have the value `Vocês têm o <name>?`.
  - Also `test_catalog_dialog_shows_field_errors`: submitting empty gives `aria-invalid="true"` on Nome and focus on it.
  Red commit `test(e2e): create a product and ask the agent (red)` only if it fails first; otherwise one commit `test(e2e): create a product and ask the agent`. `make e2e` green.

### Task 8: spec and docs sync — ~25 min

**Files:**
- Modify: `docs/superpowers/specs/2026-11-05-emporio-agent-design.md`, `docs/scaling-and-cost.md`, `README.md`, `AGENTS.md`
- Create: `docs/decisions/0011-catalog-in-postgres-hybrid-search.md`

- [ ] **Step 1:** spec:
  - **§3:** append to the "Writing store data" bullet: "The demo's Catálogo dialog is the store's back office, a separate actor from the agent: logged-in users create and edit their own products; the agent and MCP stay read-only (§7.2.6)."
  - **§7.1:** price, stock and promotion become exact SQL columns in Postgres; hybrid retrieval (FTS + trigram + vector) only proposes candidates, and facts never come from the vector side.
  - **§7.2.2:** mark the "Products: … never in SQL" line as superseded by §7.2.6.
  - **New §7.2.6 "Catalog rulings":** the ten owner decisions; pool 40 plus the grader; the category filter from `named_categories`; no NoMatch fallback; caps of 20 per login and 500 total and 10 writes/min; seed reset by `make ingest`; `product_embeddings` dropped.
  - **§7.3:** the diagram's catalog line moves from "stdlib csv (in memory)" to Postgres, with orders staying on CSV.
  - **§7.3.1:** the four `/api/catalog/*` rows (auth, body, success, errors as in Task 6) and a `ProductIn` bullet with the bounds.
- [ ] **Step 2:** `docs/decisions/0011-catalog-in-postgres-hybrid-search.md`, in the 0010 format (Context, Decision, Consequences, Alternatives). Alternatives: ParadeDB BM25 (AGPL, a new image), FTS + vector only, vector-only with post-filter (0 rows on the 8.6% filter), a queue/outbox for embeddings.
- [ ] **Step 3:** `docs/scaling-and-cost.md`, a new section "Catalog search at scale". It cites `docs/research/catalog-db.md` §6 and is labelled as local probes on a shared Mac:
  - hybrid p50 17–34 ms and p95 47–105 ms at 50,065 rows;
  - the filtered-HNSW pitfall: 0 rows and recall 0.06 without iterative scans, at least 8 of 10 and recall 0.62 with `relaxed_order`;
  - code + typo hit@5 18/18 with trigram against 13/18 without;
  - the difflib grader over 50k rows: p50 1.5 s;
  - bulk: 850 s to embed 50k rows, a 14 s HNSW build, 260 MB;
  - write path: about 9 ms embed + 7 ms upsert;
  - plus the ~80 ms Modal → Railway RTT per catalog query, and the path past ~1M rows (halfvec, BM25, a dedicated engine).
- [ ] **Step 4:** README:
  - fix the architecture line `CSVs: catálogo e pedidos, em memória` → pedidos only, with the catalog under Postgres;
  - add one short section "Catálogo no Postgres" (at most 5 lines, pt-BR): hybrid search in one query, the agent still only reads, the Catálogo dialog as the store's back office, and two or three research numbers;
  - link ADR 0011 and the research.

  `AGENTS.md`: `make ingest` reseeds the catalog and deletes products created in the demo. Commit `docs: catalog in Postgres rulings, ADR 0011 and search numbers`.

### Task 9: gates, PR, review, owner checkpoint

- [ ] **Step 1:** `make check`, `make check-web`, `make test-pg`, `make e2e` and (if code changed since Task 4) `make evals PROVIDER=gemini`, all green. Run `gitleaks` over the branch and `git grep -nE 'https://[a-z0-9-]+--[a-z0-9-]+\.modal\.run|/(Users|home)/[a-z]'`, which must be empty.
- [ ] **Step 2:** `git push -u origin feat/catalog-db` and `gh pr create` with an English body: what moved to Postgres, the eval table (golden, policies, products hit@1/hit@5 per group), the write protections, and what was cut. End it with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 3:** run the project's `reviewing-changes` skill (`.claude/skills/reviewing-changes/`) on the PR, with this plan as the phase. Apply the FIX-NOW items as new commits and re-run the gates they touch.
- [ ] **Step 4 [ASK, Modal CPU, cents]:** after the owner says yes, run `cd backend && uv run modal run ../deploy/modal_api.py::ingest`, then `make deploy-api` right after, back to back: the old API reads `product_embeddings` until it is redeployed. Smoke on the hosted demo: create a product in Catálogo, ask about it, get it with its price.
- [ ] **Step 5:** owner checkpoint before merging. Bring:
  - the PR link;
  - the eval numbers;
  - a screenshot of the Catálogo success state and the agent's answer about the new product;
  - the review verdict;
  - whether the hosted demo was re-ingested;
  - the reminder to run the manual reset (`modal run …::ingest`) after the evaluation window.
