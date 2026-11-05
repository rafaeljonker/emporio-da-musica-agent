# Phase 2 research: pure domains, use cases, CSV repositories

Date: 2026-11-05. Local facts cite file paths; PyPI versions fetched 2026-11-05 (release dates and wheel sizes were NOT retrievable from the truncated PyPI JSON, so they are unconfirmed).

## 1. CSV loading: DuckDB vs stdlib `csv`
- Data: 65 products, 50 customers, 20 orders (`data/desafio_tecnico_ai_eng - *.csv`, counted locally). Spec §7.7 shows "CSV via DuckDB" (`docs/superpowers/specs/2026-11-05-emporio-agent-design.md`).
- DuckDB latest on PyPI: 2.0.0 (https://pypi.org/pypi/duckdb/json). API: `duckdb.connect()`, `con.read_csv(path)`, `con.execute(sql).fetchall()`. The cp312 manylinux x86_64 wheel was about 20 MB for an older release (same URL; 2.0.0 size unconfirmed). Import time not measured.
- Verdict: for 65 rows DuckDB buys nothing. The CSVs have quirks (empty `notes`, JSON in `specs`, float price strings) that you parse by hand either way. `pyproject.toml` has `dependencies = []`, and `duckdb` is already in the import-linter forbidden list for domain, so it is allowed only in infrastructure.
- Recommend stdlib `csv.DictReader` (`encoding="utf-8"`, `newline=""`) in `infrastructure/csv_*_repository.py`. Keep the port: `Protocol` classes (`ProductRepository`, `OrderRepository`) live in `application/ports.py` and return domain entities. A later DuckDB/Postgres adapter implements the same Protocol and swaps in at the composition root. Domain and use cases never see rows. Revisit DuckDB only if the spec's SQL analytics demand it (unconfirmed need).

## 2. Fuzzy product search (pt-BR)
- rapidfuzz latest 3.14.6, Python >=3.11 (https://pypi.org/pypi/rapidfuzz/json). Docs: https://rapidfuzz.github.io/RapidFuzz/Usage/process.html. `process.extract(query, choices, scorer=fuzz.WRatio, processor=None, limit=5, score_cutoff=...)` returns `(choice, score, index)` tuples; scorers `fuzz.WRatio`, `fuzz.token_set_ratio` (https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html). Since 3.0 the default `processor` is None, so normalize yourself.
- Normalize in `shared/text.py`: `unicodedata.normalize("NFKD", s)`, drop `category == "Mn"` characters, `casefold()`, collapse whitespace. Python docs: https://docs.python.org/3/library/unicodedata.html.
- Plurals: a tiny token stemmer (`ões|ães|ãos` becomes `ão`; after NFKD folding, `oes|aes|aos` becomes `ao`; then strip a trailing `s` when length > 3). So violões -> violao and guitarras -> guitarra. Do not use a full stemmer (NLTK/RSLP is a new dependency; unconfirmed need).
- Category matching: build the alias set from normalized `categories.csv` names and also stem them. If the query contains a category token, filter products by that category before scoring.
- Search algorithm (pure, in domain): (1) normalized-name equality or a model-token match gives an exact hit. Example: "takamine gd20" has every token inside exactly one product name (id 95, "Takamine GD20 Dreadnought Natural"). (2) Otherwise score with `token_set_ratio`; keep results at or above a cutoff. (3) Result type `SearchResult = Exact(product) | Candidates(list) | NoMatch`. "takamine" matches 4 products (ids 95, 100, 105, 115 in `products.csv`), so it returns `Candidates` and the agent asks for clarification. Rule: if more than one product matches at the top score tier, return candidates, never pick one.

## 3. Money and installments
- Parse prices with `Decimal(str_value)`, and `quantize(Decimal("0.01"), ROUND_HALF_UP)` for every derived value. Products have values like `599.9` and `849`; no value has more than 2 decimals (checked locally). Docs: https://docs.python.org/3/library/decimal.html. Wrap in a frozen `Money` dataclass in `shared/money.py`.
- Format without locale: `f"{v:,.2f}"`, then swap separators via `translate` ("," to ".", "." to ","), so you get "R$ 1.967,18".
- Policy 3 (`data/políticas_da_loja.pdf`, read with pdftotext): PIX is "5% de desconto sobre o preço de tabela", debit and boleto are in cash, and credit goes "Até 12x sem juros, Parcela mínima de R$ 100,00".
- Policy 3.1: "até 3x: sem juros, sem valor mínimo de parcela (exceto abaixo de R$ 50,00)"; 4–6x min parcel R$ 80; 7–12x min parcel R$ 100; combining payment forms allowed above R$ 2.000,00.
- Ambiguities (flag as documented assumptions): (a) the table's "min R$ 100" conflicts with the 3.1 tiers. Treat 3.1 as the specific rule that wins. (b) "except below R$ 50,00" is read as a minimum parcel of R$ 50 for 2–3x, so an order under R$ 100 cannot be split into 2x or more. Rule: `n` is allowed iff `total/n >= min_for(n)`, with min_for = 50 for n in 2..3, 80 for 4..6, 100 for 7..12; 1x is always allowed. Compare unrounded or rounded? Use the rounded parcel (ROUND_HALF_UP). Ceiling note: the sum of parcels may differ by cents; show "n x R$ X (sem juros)".
- Promotions (6.2): "promoções não são cumulativas. O desconto de PIX (5%) não se aplica sobre preços já promocionais." Also: a promotional price must be shown with the original price and the percentage (6.2 Comunicação). Rule: `pix_price = table_price*0.95` only when no active promotion (`is_active == 1`); otherwise the promo price is the final price, with no PIX discount.

## 4. Dates and clock
- `shared/clock.py`: `Clock` Protocol with `now() -> datetime` (aware) and `today() -> date`. `SystemClock` uses `datetime.now(ZoneInfo("America/Campo_Grande"))` (satisfies ruff DTZ). `FixedClock` for tests. Docs: https://docs.python.org/3/library/zoneinfo.html. `tzdata` may be needed on systems without an OS tz database (unconfirmed on the target Docker image).
- Inject `STORE_TODAY` through config into a `FixedClock` for evals and demos. The data runs from 2025-10 to 2025-11, so real "today" would break the windows.
- Regret window (4.1): 7 calendar days after receipt. Defect (4.2): 30 days after purchase. 4.3 preference exchange: 7 days. 4.4: ineligible items.
- The data has only `estimated_delivery`, no actual delivery. Assumption: for `delivered` orders, delivery date = `estimated_delivery`, and the answer must say so ("com base na previsão de entrega"). Cancelled orders have an empty `estimated_delivery` (`orders.csv`) and are never eligible. Defect window counts from `order_date`. The window is inclusive: eligible if `today <= delivery + 7 days`.

## 5. Customer identity
- Phone: keep digits only; strip a leading `55` when length is 12 or 13; compare the last 10–11 digits (DDD + number). CSV format "(67) 98432-1098". Email: `strip().casefold()`.
- Match when the order's `customer_id` matches the supplied phone OR email. On any mismatch raise `IdentityMismatch` with no data in the message, and the tool answer must not hint at which field failed or whether the order exists.

## 6. Domain modeling
- Frozen `@dataclass(frozen=True, slots=True)`, per `.claude/rules/python-style.md`. Pydantic only at the edges. attrs is not needed (no deps).
- `StrEnum` for `ProductStatus`, `OrderStatus`, `PaymentMethod` (`pix`, `credit_6x`, ... parsed in the repository).
- Domain exceptions inherit from a shared `DomainError`: `ProductNotFound`, `OrderNotFound`, `IdentityMismatch`, `InvalidInstallments`. Ruff TRY requires them, and no bare `ValueError`.
- Ports: `typing.Protocol` in `application/`. Under basedpyright strict, annotate everything, avoid `Any`, and use `Sequence[Product]` returns. Tuple fields instead of lists keep the dataclasses truly immutable.

## 7. Testing
- Layout `backend/tests/unit/<context>/test_*.py`. Add `addopts = ["--import-mode=importlib"]` to `[tool.pytest.ini_options]`. Reason: the default `prepend` mode needs unique test basenames when tests directories lack `__init__.py`, and `catalog` and `orders` will have e.g. `test_repository.py` twice. Docs: https://docs.pytest.org/en/stable/explanation/pythonpath.html. Confirmed behavior; not yet applied in `backend/pyproject.toml`.
- Fixtures: the domain and use-case tests use small in-memory fakes. A few integration tests in `tests/integration/` load the real CSVs to pin the traps from spec §7.6 (4 Takamine, 2 discontinued, 1 coming_soon, 4 of 25 promotions active, cancelled orders with notes). Use `emporio.paths` for the data location.
- Hypothesis latest 6.170.14 (https://pypi.org/pypi/hypothesis/json). Worth a few properties for money and installments only (e.g. n allowed implies parcel >= minimum; PIX price <= table price; parcel x n within n cents of the total). It is a dev-only dependency. Skip it elsewhere.
- Name tests as behaviors: `test_pix_discount_is_not_applied_on_promotional_price`, `test_takamine_alone_returns_four_candidates`.

## Recommended decisions for phase 2
1. Use stdlib `csv`, not DuckDB; keep `Protocol` repository ports in `application/` so a DuckDB/Postgres adapter can replace them.
2. Add `rapidfuzz` (3.14.6) as the only new runtime dependency; normalize with NFKD plus casefold plus a small plural stemmer in `shared/text.py`; search returns `Exact | Candidates | NoMatch`.
3. Money: `Decimal(str)` with ROUND_HALF_UP on 2 places; manual pt-BR formatting; installment rule per 3.1 (parcel minimum R$ 50 for 2–3x, 80 for 4–6x, 100 for 7–12x), documented as an interpretation; promos never combine with the PIX 5%.
4. Clock Protocol with `ZoneInfo("America/Campo_Grande")`, `FixedClock` for tests, `STORE_TODAY` injected; delivery date for delivered orders = `estimated_delivery`, with an explicit caveat in the reply.
5. Identity: digits-only phone (strip 55), casefolded email; opaque `IdentityMismatch`.
6. Frozen dataclasses, `StrEnum`, domain exceptions, `Protocol` ports; add `--import-mode=importlib` and `tests/unit/<context>/` now; hypothesis (dev) only for money/installments.
