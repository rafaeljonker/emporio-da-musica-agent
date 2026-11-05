import pytest

from emporio.catalog.application.get_product import GetProduct
from emporio.catalog.application.list_promotions import ListPromotions
from emporio.catalog.application.quote_installments import QuoteInstallments
from emporio.catalog.application.search_products import SearchProducts
from emporio.catalog.domain.errors import ProductNotFound
from emporio.catalog.domain.product import ProductStatus
from emporio.catalog.domain.search import Exact
from tests.unit.catalog.factories import category, m, product, promo
from tests.unit.catalog.fakes import FakeCatalogRepository


def test_get_product_quotes_with_active_promotion() -> None:
    repo = FakeCatalogRepository(
        (product(id=1, price="1000"),),
        (),
        (
            promo(id=1, product_id=1, percent="10", active=False),
            promo(id=2, product_id=1, percent="20"),
        ),
    )
    found, quote = GetProduct(repo)(1)
    assert found.id == 1
    assert quote.final == m("800")
    assert quote.promotion is not None
    assert quote.promotion.id == 2
    assert quote.pix is None


def test_get_product_without_promotion_has_pix() -> None:
    repo = FakeCatalogRepository((product(id=1, price="1000"),))
    _, quote = GetProduct(repo)(1)
    assert quote.final == m("1000")
    assert quote.pix == m("950")


def test_get_product_picks_highest_active_percent() -> None:
    repo = FakeCatalogRepository(
        (product(id=1, price="1000"),),
        (),
        (promo(id=1, product_id=1, percent="10"), promo(id=2, product_id=1, percent="15")),
    )
    assert GetProduct(repo)(1)[1].final == m("850")


def test_get_product_not_found() -> None:
    with pytest.raises(ProductNotFound):
        GetProduct(FakeCatalogRepository())(99)


def test_list_promotions_only_active_on_available_sorted() -> None:
    repo = FakeCatalogRepository(
        (
            product(id=1, name="Zeta"),
            product(id=2, name="Alfa"),
            product(id=3, name="Fora", status=ProductStatus.DISCONTINUED),
            product(id=4, name="Sem estoque", stock=0),
            product(id=5, name="Inativa"),
        ),
        (),
        (
            promo(id=1, product_id=1),
            promo(id=2, product_id=2),
            promo(id=3, product_id=3),
            promo(id=4, product_id=4),
            promo(id=5, product_id=5, active=False),
            promo(id=6, product_id=99),
        ),
    )
    assert [p.name for p, _ in ListPromotions(repo)()] == ["Alfa", "Zeta"]


def test_quote_installments_defaults_to_max_and_accepts_count() -> None:
    assert QuoteInstallments()(m("1200")).count == 12
    assert QuoteInstallments()(m("1200"), 3).count == 3


def test_search_products_delegates_to_domain() -> None:
    repo = FakeCatalogRepository(
        (product(id=1, name="Violao Giannini", category_id=1),), (category(id=1, name="Violoes"),)
    )
    assert isinstance(SearchProducts(repo)("Violao Giannini"), Exact)


def test_list_promotions_uses_highest_active_percent_per_product() -> None:
    repo = FakeCatalogRepository(
        (product(id=1, price="1000"),),
        (),
        (
            promo(id=1, product_id=1, percent="30", active=False),
            promo(id=2, product_id=1, percent="10"),
            promo(id=3, product_id=1, percent="20"),
        ),
    )
    ((_, quote),) = ListPromotions(repo)()
    assert quote.promotion is not None
    assert quote.promotion.percent == 20
    assert quote.final == m("800")
