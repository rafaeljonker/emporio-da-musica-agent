# Phase 2: Pure domains (catalog, orders, shared) — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** implement the store rules the agent depends on, as pure, tested Python: money and pt-BR formatting, text normalization, clock, catalog (availability, promo/PIX pricing, installments, product search) and orders (identity check, status, return eligibility), plus CSV repositories over the case data.

**Architecture:**
- `domain/` holds frozen dataclasses and pure functions (stdlib + `emporio.shared` only).
- `application/` holds `Protocol` repository ports and one use case per file.
- `infrastructure/` holds the stdlib-`csv` adapters reading `data/` through `emporio.paths`.
- Unit tests use in-memory fakes. A few integration tests pin the data traps against the real CSVs.

**Tech stack:** Python 3.12 stdlib (`decimal`, `csv`, `difflib`, `unicodedata`, `zoneinfo`, `enum.StrEnum`, `dataclasses`, `typing.Protocol`), pytest, hypothesis (dev only).

**Spec:** `docs/superpowers/specs/2026-11-05-emporio-agent-design.md` §7.2, §7.3, §7.6, §7.7. **Research:** `docs/research/fase-2.md`.

## Global Constraints
- **Branch and commits:** branch `feat/domains`. TDD pairs per behavior: `test(<ctx>): <behavior> (red)` then `feat(<ctx>): <behavior>`. Commit subject ≤ 72 chars, imperative, with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Gates:** `make check` must be green on every commit except the `(red)` commit, where only the new test may fail.
- **Dependencies:** no new runtime dependencies. Dev only: `hypothesis`.
- **Layering:** domain code imports only stdlib and `emporio.shared`. The 9 import-linter contracts must stay kept.
- **Domain modeling:**
  - money is `Decimal` (never `float`), wrapped in `emporio.shared.money.Money`;
  - entities are `@dataclass(frozen=True, slots=True)`, with tuples instead of lists;
  - statuses are `StrEnum`;
  - errors are subclasses of `emporio.shared.errors.DomainError`;
  - time comes only through `emporio.shared.clock.Clock`.
- **Store rules** (the store policy is the source of truth; ambiguous points are recorded in `docs/research/fase-2.md` §3):
  - **PIX:** 5% off the table price, only when the product has no active promotion. Promotions never stack with PIX (policy 6.2).
  - **Promotions:** active only if `is_active == 1`. Shown as original + % + final.
  - **Installments, interest-free:** n=1 is always allowed. For n in 2..3 the minimum parcel is R$ 50.00, for 4..6 it is R$ 80.00, for 7..12 it is R$ 100.00. Max 12. The parcel is rounded half-up to cents.
  - **Availability:** a product is available iff `status == active` and `stock > 0`.
  - **Regret window:** 7 calendar days counted from the delivery date. For delivered orders, the delivery date is `estimated_delivery` (documented assumption). Only `delivered` orders are eligible.
  - **Defect window:** 30 days from `order_date`, for `delivered` orders only.
  - **Identity:**
    - phone matches on digits only, after stripping a leading `55` when 12–13 digits remain;
    - email matches casefolded and stripped;
    - a mismatch raises `IdentityMismatch` with no order details.
- **Defaults:** the store timezone is `America/Campo_Grande`. The default `STORE_TODAY` for demos and evals is `2026-02-20`.
- **Test conventions:** test names describe behaviors. Unit tests live in `backend/tests/unit/<context>/`, integration tests in `backend/tests/integration/`.

## Review Focus
1. **Ambiguous product name** ("takamine", four products). Expected: `Candidates` with all four, never a guess. Test: Task 4 `test_brand_only_query_returns_all_candidates` and Task 6 `test_takamine_returns_four_candidates`.
2. **Promo price with PIX.** Expected: no PIX discount on a promotional price. Test: Task 3 `test_pix_price_is_absent_when_promotion_active`.
3. **Order lookup with another customer's email.** Expected: `IdentityMismatch`, no status leaked. Test: Task 8 `test_get_order_status_rejects_wrong_identity`.
4. **Phone typed as "+55 (67) 98432-1098" or "67984321098".** Expected: both match `(67) 98432-1098`. Test: Task 7 `test_phone_matches_with_country_code_and_formatting`.
5. **Return question for a cancelled order or one with no delivery date.** Expected: not eligible, with a reason, no crash on the empty date. Test: Task 7 `test_cancelled_order_is_not_eligible`.

---

### Task 1: shared money and errors (+ pytest/hypothesis config)

**Files:**
- Create: `backend/src/emporio/shared/money.py`, `backend/src/emporio/shared/errors.py`
- Modify: `backend/pyproject.toml`. Add `addopts = ["--import-mode=importlib"]` under `[tool.pytest.ini_options]` and add `hypothesis` with `uv add --dev hypothesis`.
- Test: `backend/tests/unit/shared/test_money.py`

**Interfaces (produces):**
- `class DomainError(Exception)`
- `@dataclass(frozen=True, slots=True) class Money: amount: Decimal` (always quantized to 0.01, ROUND_HALF_UP, in `__post_init__` via `object.__setattr__`)
- `Money.from_str(value: str) -> Money` (`Decimal(value)`; raises `DomainError` on an invalid value)
- `Money.percent_off(self, percent: Decimal) -> Money`
- `Money.divided_by(self, parts: int) -> Money`
- `Money.__add__`, `__lt__`, `__le__`
- `format_brl(money: Money) -> str` (e.g. `"R$ 1.967,18"`, `"R$ 599,90"`, `"R$ 0,05"`; no locale)

- [ ] **Step 1: failing tests**
```python
def test_from_str_quantizes_half_up(): assert Money.from_str("599.9").amount == Decimal("599.90")
def test_percent_off_rounds_half_up(): assert Money.from_str("2399").percent_off(Decimal("18")) == Money.from_str("1967.18")
def test_pix_style_discount(): assert Money.from_str("2199").percent_off(Decimal("5")) == Money.from_str("2089.05")
def test_format_brl_uses_dot_thousands_and_comma_decimals(): assert format_brl(Money.from_str("1967.18")) == "R$ 1.967,18"
def test_format_brl_small_value(): assert format_brl(Money.from_str("0.05")) == "R$ 0,05"
def test_from_str_rejects_garbage():
    with pytest.raises(DomainError): Money.from_str("abc")
@given(st.decimals(min_value=0, max_value=100000, places=2), st.integers(min_value=0, max_value=100))
def test_percent_off_never_exceeds_original(value, pct): assert Money(value).percent_off(Decimal(pct)) <= Money(value)
```
- [ ] **Step 2:** `cd backend && uv run pytest tests/unit/shared -q`. Expected: FAIL (ImportError).
- [ ] **Step 3:** implement `money.py` and `errors.py` (basedpyright strict).
- [ ] **Step 4:** `make check`. Expected: green.
- [ ] **Step 5: commits.** `test(shared): money arithmetic and pt-BR formatting (red)`, then `feat(shared): add Money value object and DomainError`, plus `chore(backend): enable importlib test mode and hypothesis`.

### Task 2: shared text normalization and clock

**Files:**
- Create: `backend/src/emporio/shared/text.py`, `backend/src/emporio/shared/clock.py`
- Test: `backend/tests/unit/shared/test_text.py`, `backend/tests/unit/shared/test_clock.py`

**Interfaces (produces):**
- `fold(text: str) -> str`: NFKD, drop combining marks, casefold, collapse whitespace.
- `tokens(text: str) -> tuple[str, ...]`: `fold` plus split on non-alphanumerics, plus `stem` for each token.
- `stem(token: str) -> str`: `oes|aes|aos` becomes `ao`, then strip a trailing `s` when `len > 3`.
- `class Clock(Protocol): def today(self) -> date: ...`
- `STORE_TZ = ZoneInfo("America/Campo_Grande")`
- `class SystemClock`: `today()` returns `datetime.now(STORE_TZ).date()`.
- `@dataclass(frozen=True) class FixedClock: fixed: date`
- `DEFAULT_STORE_TODAY = date(2026, 2, 20)`

- [ ] **Step 1: failing tests**
```python
def test_fold_removes_accents_and_case(): assert fold("  Violão  ELÉTRICO ") == "violao eletrico"
def test_tokens_stem_plurals(): assert tokens("Violões e guitarras") == ("violao", "e", "guitarra")
def test_stem_keeps_short_words(): assert stem("gs") == "gs"
def test_tokens_split_model_codes(): assert tokens("Takamine GD-20") == ("takamine", "gd", "20")
def test_fixed_clock_returns_fixed_date(): assert FixedClock(date(2026, 2, 20)).today() == date(2026, 2, 20)
def test_system_clock_uses_store_timezone(): assert isinstance(SystemClock().today(), date)
```
- [ ] **Step 2:** run, expect FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** `make check` green.
- [ ] **Step 5: commits.** `test(shared): text folding, plural stemming and clock (red)`, then `feat(shared): add text normalization and store clock`.

### Task 3: catalog domain (product, promotion, pricing, installments)

**Files:**
- Create: `backend/src/emporio/catalog/domain/{product.py,pricing.py,installments.py}`
- Test: `backend/tests/unit/catalog/test_pricing.py`, `test_installments.py`, `test_product.py`

**Interfaces (produces):**
- `class ProductStatus(StrEnum): ACTIVE="active"; DISCONTINUED="discontinued"; COMING_SOON="coming_soon"`
- `@dataclass(frozen=True, slots=True) class Category: id: int; name: str; description: str`
- `@dataclass(frozen=True, slots=True) class Product: id: int; name: str; category_id: int; description: str; price: Money; stock: int; status: ProductStatus; specs: tuple[tuple[str, str], ...]`, with `property is_available -> bool`.
- `@dataclass(frozen=True, slots=True) class Promotion: id: int; product_id: int; percent: Decimal; label: str; active: bool`
- `@dataclass(frozen=True, slots=True) class PriceQuote: table: Money; promotion: Promotion | None; final: Money; pix: Money | None`
- `quote_price(product: Product, promotion: Promotion | None) -> PriceQuote`. An inactive promotion is ignored. With an active promotion, `final = table.percent_off(promo.percent)` and `pix = None`. Otherwise `final = table` and `pix = table.percent_off(5)`.
- `PIX_DISCOUNT = Decimal("5")`
- `@dataclass(frozen=True, slots=True) class InstallmentPlan: count: int; parcel: Money`
- `max_installments(total: Money) -> InstallmentPlan`: the largest n in 1..12 that satisfies the minimums in Global Constraints.
- `installment_plan(total: Money, count: int) -> InstallmentPlan`: raises `InvalidInstallments(DomainError)` when n is not allowed or is outside 1..12.

- [ ] **Step 1: failing tests**
```python
def test_unavailable_when_out_of_stock(): assert not product(stock=0).is_available
def test_unavailable_when_discontinued_even_with_stock(): assert not product(stock=13, status=ProductStatus.DISCONTINUED).is_available
def test_coming_soon_is_unavailable(): assert not product(stock=2, status=ProductStatus.COMING_SOON).is_available
def test_pix_is_five_percent_off_table_without_promotion():
    q = quote_price(product(price="2199"), None); assert q.final == m("2199") and q.pix == m("2089.05")
def test_pix_price_is_absent_when_promotion_active():
    q = quote_price(product(price="2399"), promo(percent="18", active=True)); assert q.final == m("1967.18") and q.pix is None
def test_inactive_promotion_is_ignored(): assert quote_price(product(price="2399"), promo(percent="18", active=False)).final == m("2399")
def test_900_allows_9_installments_of_100(): assert max_installments(m("900")) == InstallmentPlan(9, m("100"))
def test_90_allows_only_one_installment(): assert max_installments(m("90")).count == 1
def test_150_allows_three_of_50(): assert max_installments(m("150")) == InstallmentPlan(3, m("50"))
def test_twelve_installments_of_2199(): assert installment_plan(m("2199"), 12).parcel == m("183.25")
def test_rejects_13_installments():
    with pytest.raises(InvalidInstallments): installment_plan(m("5000"), 13)
@given(st.decimals(min_value=1, max_value=50000, places=2))
def test_max_installments_respects_minimum(total): plan = max_installments(Money(total)); assert plan.count == 1 or plan.parcel.amount >= minimum_for(plan.count)
```
(`product()`, `promo()` and `m()` are small factories in `tests/unit/catalog/factories.py`; `minimum_for` is exported from `installments.py`.)
- [ ] **Step 2:** run, expect FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** `make check` green.
- [ ] **Step 5: commits.** One red/green pair per file (product, pricing, installments).

### Task 4: catalog domain search

**Files:**
- Create: `backend/src/emporio/catalog/domain/search.py`
- Test: `backend/tests/unit/catalog/test_search.py`

**Interfaces:**
- **Consumes:** `Product`, `Category` (Task 3); `tokens` (Task 2).
- **Produces:**
  - `@dataclass(frozen=True) class Exact: product: Product`
  - `@dataclass(frozen=True) class Candidates: products: tuple[Product, ...]`
  - `@dataclass(frozen=True) class NoMatch: ...`
  - `SearchResult = Exact | Candidates | NoMatch`
  - `search_products(products: Sequence[Product], categories: Sequence[Category], query: str, max_price: Money | None = None, include_unavailable: bool = False) -> SearchResult`

**Algorithm** (one `difflib`-based fuzzy fallback; no third-party library):
1. Category filter: if any query token (stemmed) equals a stemmed token of a category name, keep only that category's products. Remove category tokens from the query.
2. Drop products above `max_price` (compared on table price), and unavailable products unless `include_unavailable`.
3. Token containment: products whose name tokens contain all remaining query tokens.
   - exactly 1 product: `Exact`;
   - 2 or more: `Candidates`, sorted by price;
   - no tokens left after the category filter: `Candidates` with every remaining product, sorted by price (e.g. "violão até 1000").
4. Fuzzy fallback only when step 3 finds nothing: score each product with `difflib.SequenceMatcher(None, " ".join(query_tokens), " ".join(name_tokens)).ratio()`. Keep scores ≥ 0.6. Return the top tier (within 0.05 of the best) as `Exact` if it holds 1 product, `Candidates` if more. If nothing passes, `NoMatch`.

- [ ] **Step 1: failing tests** (in-memory catalog with 4 Takamine products, 2 violões ≤ 1000, 1 discontinued 7-string, 1 guitarra)
```python
def test_exact_model_query_returns_exact(): assert isinstance(search(catalog, "Takamine GD20"), Exact)
def test_brand_only_query_returns_all_candidates(): r = search(catalog, "takamine"); assert isinstance(r, Candidates) and len(r.products) == 4
def test_category_plural_with_max_price(): r = search(catalog, "violões", max_price=m("1000")); assert isinstance(r, Candidates) and all(p.price <= m("1000") for p in r.products)
def test_unavailable_products_hidden_by_default(): assert isinstance(search(catalog, "Shelby SN-7C"), NoMatch)
def test_unavailable_included_when_asked(): assert isinstance(search(catalog, "Shelby SN-7C", include_unavailable=True), Exact)
def test_typo_falls_back_to_fuzzy(): assert isinstance(search(catalog, "takamine gd 2O"), Exact)
def test_unknown_returns_no_match(): assert isinstance(search(catalog, "bateria eletronica roland"), NoMatch)
```
- [ ] **Step 2:** run, expect FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** `make check` green.
- [ ] **Step 5: commits.** `test(catalog): product search tiers (red)`, then `feat(catalog): add product search with exact, candidates and fuzzy tiers`.

### Task 5: catalog application (ports and use cases)

**Files:**
- Create: `backend/src/emporio/catalog/application/{ports.py,search_products.py,get_product.py,list_promotions.py,quote_installments.py}`
- Test: `backend/tests/unit/catalog/test_use_cases.py` (in-memory fake repository in `tests/unit/catalog/fakes.py`)

**Interfaces:**
- **Ports:** `class CatalogRepository(Protocol)` with:
  - `def products(self) -> Sequence[Product]`
  - `def categories(self) -> Sequence[Category]`
  - `def promotions(self) -> Sequence[Promotion]`
- **Use cases** (each is a class taking the repository in its constructor, with `__call__`):
  - `SearchProducts(repo)(query: str, max_price: Money | None = None, include_unavailable: bool = False) -> SearchResult`
  - `GetProduct(repo)(product_id: int) -> tuple[Product, PriceQuote]`, raises `ProductNotFound(DomainError)`
  - `ListPromotions(repo)() -> tuple[tuple[Product, PriceQuote], ...]`: only active promotions on available products.
  - `QuoteInstallments()(total: Money, count: int | None = None) -> InstallmentPlan`: max plan when `count` is None.

- [ ] **Step 1: failing tests:** a quote with promotion, `ProductNotFound`, the promotions list excluding inactive and unavailable items, the installment default being max.
- [ ] **Step 2:** run, expect FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** `make check` green.
- [ ] **Step 5: commits.** `test(catalog): use cases (red)`, then `feat(catalog): add catalog ports and use cases`.

### Task 6: catalog CSV repository + data-trap integration tests

**Files:**
- Create: `backend/src/emporio/catalog/infrastructure/csv_catalog_repository.py`
- Test: `backend/tests/integration/test_catalog_data.py`

**Interfaces:**
- **Consumes:** `emporio.paths.CASE_CSV_FILES`.
- **Produces:** `CsvCatalogRepository(files: Mapping[str, Path] = CASE_CSV_FILES)`, which implements `CatalogRepository`.
  - Rows are loaded once and cached.
  - `specs` JSON is parsed with `json.loads` into sorted `(key, str(value))` tuples.
  - Bad rows raise `DomainError` with the row number.

- [ ] **Step 1: failing integration tests** (real data)
```python
def test_takamine_returns_four_candidates(): assert len(SearchProducts(repo)("takamine").products) == 4
def test_gd20_price_and_pix(): _, q = GetProduct(repo)(95); assert q.final == m("2199") and q.pix == m("2089.05")
def test_four_active_promotions(): assert {p.id for p, _ in ListPromotions(repo)()} == {127, 121, 90, 94}
def test_crafter_ht100_promo(): _, q = GetProduct(repo)(90); assert q.final == m("1967.18") and q.pix is None
def test_discontinued_and_coming_soon_are_unavailable(): assert {p.id for p in repo.products() if not p.is_available} >= {113, 130, 136, 96}
def test_c40_is_cheapest_beginner_violao_under_1000(): r = SearchProducts(repo)("violão", max_price=m("1000")); assert any(p.id == 81 for p in r.products)
```
- [ ] **Step 2:** run, expect FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** `make check` green (`lint-imports` must keep the `csv` and `json` IO in infrastructure).
- [ ] **Step 5: commits.** `test(catalog): data traps on real CSVs (red)`, then `feat(catalog): add CSV catalog repository`.

### Task 7: orders domain (order, customer identity, returns)

**Files:**
- Create: `backend/src/emporio/orders/domain/{order.py,identity.py,return_policy.py}`
- Test: `backend/tests/unit/orders/test_identity.py`, `test_return_policy.py`

**Interfaces (produces):**
- `class OrderStatus(StrEnum)`: pending, confirmed, shipped, delivered, cancelled.
- `@dataclass(frozen=True, slots=True) class Customer: id: int; name: str; phone: str; email: str; city: str`
- `@dataclass(frozen=True, slots=True) class OrderItem: product_id: int; quantity: int`
- `@dataclass(frozen=True, slots=True) class Order: id: int; customer_id: int; order_date: date; status: OrderStatus; total: Money; payment_method: str; tracking_code: str | None; estimated_delivery: date | None; notes: str | None; items: tuple[OrderItem, ...]`
- `normalize_phone(raw: str) -> str` (digits only; strip a leading `55` when the result has 12–13 digits)
- `matches_identity(customer: Customer, email_or_phone: str) -> bool`
- `class IdentityMismatch(DomainError)`
- `@dataclass(frozen=True) class ReturnEligibility: regret_eligible: bool; defect_eligible: bool; delivered_on: date | None; regret_deadline: date | None; defect_deadline: date | None; reason: str`
- `check_return(order: Order, today: date) -> ReturnEligibility`. `reason` is an English machine-readable code: `not_delivered`, `cancelled`, `within_regret_window`, `regret_window_closed`, `within_defect_window`, `defect_window_closed`.
- `REGRET_DAYS = 7`, `DEFECT_DAYS = 30`

- [ ] **Step 1: failing tests**
```python
def test_phone_matches_with_country_code_and_formatting(): assert matches_identity(cust(phone="(67) 98432-1098"), "+55 (67) 98432-1098") and matches_identity(cust(phone="(67) 98432-1098"), "67984321098")
def test_email_matches_case_insensitive(): assert matches_identity(cust(email="pedro.oliveira@jmail.com"), " Pedro.Oliveira@JMAIL.com ")
def test_wrong_email_does_not_match(): assert not matches_identity(cust(email="a@b.com"), "joao.silva@gmail.com")
def test_regret_within_seven_days_of_delivery(): e = check_return(order(status=DELIVERED, estimated_delivery=date(2026,2,17)), today=date(2026,2,20)); assert e.regret_eligible and e.regret_deadline == date(2026,2,24)
def test_regret_closed_after_seven_days(): assert not check_return(order(status=DELIVERED, estimated_delivery=date(2026,1,18)), today=date(2026,2,20)).regret_eligible
def test_cancelled_order_is_not_eligible(): e = check_return(order(status=CANCELLED, estimated_delivery=None), today=date(2026,2,20)); assert not e.regret_eligible and e.reason == "cancelled"
def test_shipped_order_is_not_yet_eligible(): assert check_return(order(status=SHIPPED), today=date(2026,2,20)).reason == "not_delivered"
def test_defect_within_thirty_days_of_purchase(): assert check_return(order(status=DELIVERED, order_date=date(2026,2,3), estimated_delivery=date(2026,2,17)), today=date(2026,2,20)).defect_eligible
```
- [ ] **Step 2:** run, expect FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** `make check` green.
- [ ] **Step 5: commits.** One red/green pair each for identity and return policy.

### Task 8: orders application (ports and use cases)

**Files:**
- Create: `backend/src/emporio/orders/application/{ports.py,get_order_status.py,list_customer_orders.py,check_return_eligibility.py}`
- Test: `backend/tests/unit/orders/test_use_cases.py` (fakes in `tests/unit/orders/fakes.py`)

**Interfaces:**
- **Ports:**
  - `class OrderRepository(Protocol)`: `def by_id(self, order_id: int) -> Order | None`, `def by_customer(self, customer_id: int) -> Sequence[Order]`
  - `class CustomerRepository(Protocol)`: `def by_id(self, customer_id: int) -> Customer | None`
- **Use cases:**
  - `GetOrderStatus(orders, customers)(order_id: int, email_or_phone: str) -> Order`. It raises `OrderNotFound(DomainError)`, and raises `IdentityMismatch` when the identity doesn't match the order's customer. **The same `IdentityMismatch` is raised when the order does not exist**, so an attacker cannot enumerate order ids. Only an identified channel path may distinguish the two.
  - `ListCustomerOrders(orders)(customer_id: int) -> tuple[Order, ...]`, newest first.
  - `CheckReturnEligibility(orders, clock)(order_id: int, customer_id: int) -> ReturnEligibility`. Raises `IdentityMismatch` if the order does not belong to `customer_id`.

- [ ] **Step 1: failing tests:**
  - `test_get_order_status_returns_order_for_matching_identity`;
  - `test_get_order_status_rejects_wrong_identity`;
  - `test_unknown_order_and_wrong_identity_are_indistinguishable`;
  - `test_list_customer_orders_newest_first`;
  - `test_return_eligibility_refuses_other_customers_order`;
  - `test_return_eligibility_uses_injected_clock`.
- [ ] **Step 2:** run, expect FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** `make check` green.
- [ ] **Step 5: commits.** `test(orders): use cases (red)`, then `feat(orders): add order ports and use cases`.

### Task 9: orders CSV repository + data-trap integration tests

**Files:**
- Create: `backend/src/emporio/orders/infrastructure/csv_order_repository.py`
- Test: `backend/tests/integration/test_orders_data.py`

**Interfaces (produces):** `CsvOrderRepository(files: Mapping[str, Path] = CASE_CSV_FILES)`, implementing `OrderRepository` and `CustomerRepository`.
- `estimated_delivery` and `tracking_code` map to `None` when empty.
- Items are joined from `order_items.csv`.

- [ ] **Step 1: failing integration tests** (real data, `FixedClock(date(2026, 2, 20))`):
  - order 7 (customer 14) is regret-eligible;
  - order 5 is not;
  - order 17 (cancelled) is not eligible;
  - `GetOrderStatus(5, <customer 5 email>)` returns `delivered`;
  - `GetOrderStatus(5, "joao.silva@gmail.com")` raises `IdentityMismatch`;
  - customer 3 has 2 orders, newest first.
- [ ] **Step 2:** run, expect FAIL.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** `make check` green.
- [ ] **Step 5: commits.** `test(orders): data traps on real CSVs (red)`, then `feat(orders): add CSV order repository`.

### Task 10: spec sync, PR and review
- [ ] **Step 1: spec sync.** Update spec §7.2/§7.3 with the phase-2 rulings: stdlib `csv` instead of DuckDB (the port allows swapping), `difflib` instead of rapidfuzz (the domain stays stdlib-only), and `STORE_TODAY` defaulting to 2026-02-20. Also update `AGENTS.md`'s gotchas if anything new appears. Commit: `docs(spec): record phase 2 data and search decisions`.
- [ ] **Step 2:** `git push -u origin feat/domains`, then `gh pr create` with an English body ending in `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 3:** run the `reviewing-changes` skill on the PR. Apply the FIX-NOW items.
- [ ] **Step 4:** checkpoint with the owner before merging.
