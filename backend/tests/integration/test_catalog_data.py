from emporio.catalog.application.get_product import GetProduct
from emporio.catalog.application.list_promotions import ListPromotions
from emporio.catalog.application.quote_installments import QuoteInstallments
from emporio.catalog.application.search_products import SearchProducts
from emporio.catalog.domain.search import Candidates, Exact
from emporio.catalog.infrastructure.csv_catalog_repository import CsvCatalogRepository
from emporio.shared.money import Money

repo = CsvCatalogRepository()


def m(value: str) -> Money:
    return Money.from_str(value)


def test_takamine_returns_four_candidates() -> None:
    assert len(SearchProducts(repo)("takamine").products) == 4  # type: ignore[union-attr]


def test_gd20_price_and_pix() -> None:
    _, q = GetProduct(repo)(95)
    assert q.final == m("2199")
    assert q.pix == m("2089.05")


def test_gd20_installments_max_12x() -> None:
    _, q = GetProduct(repo)(95)
    plan = QuoteInstallments()(q.final)
    assert plan.count == 12
    assert plan.parcel == m("183.25")


def test_four_active_promotions() -> None:
    assert {p.id for p, _ in ListPromotions(repo)()} == {127, 121, 90, 94}


def test_crafter_ht100_promo() -> None:
    _, q = GetProduct(repo)(90)
    assert q.final == m("1967.18")
    assert q.pix is None


def test_discontinued_and_coming_soon_are_unavailable() -> None:
    assert {p.id for p in repo.products() if not p.is_available} >= {113, 130, 136, 96}


def test_c40_is_cheapest_beginner_violao_under_1000() -> None:
    r = SearchProducts(repo)("violão", max_price=m("1000"))
    assert isinstance(r, Candidates)
    assert any(p.id == 81 for p in r.products)


def test_typo_gd_2o_is_exact_95() -> None:
    r = SearchProducts(repo)("takamine gd 2O")
    assert isinstance(r, Exact)
    assert r.product.id == 95


def test_typo_violuao_finds_c40() -> None:
    r = SearchProducts(repo)("violuao")
    assert isinstance(r, Candidates)
    assert any(p.id == 81 for p in r.products)
