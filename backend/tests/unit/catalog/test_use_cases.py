from decimal import Decimal

from emporio.catalog.application.get_product import GetProduct
from emporio.catalog.application.list_promotions import ListPromotions
from emporio.catalog.application.ports import CatalogFilter
from emporio.catalog.application.quote_installments import QuoteInstallments
from emporio.catalog.application.search_products import SearchProducts
from emporio.catalog.domain.errors import CatalogErrorCode
from emporio.catalog.domain.installments import InstallmentPlan
from emporio.catalog.domain.pricing import PriceQuote
from emporio.catalog.domain.product import Product, ProductStatus
from emporio.catalog.domain.search import Exact
from emporio.shared.money import Money
from emporio.shared.result import Err, Ok, Result
from tests.unit.catalog.factories import category, m, product, promo
from tests.unit.catalog.fakes import FakeCatalogRepository


def found(
    result: Result[tuple[Product, PriceQuote], CatalogErrorCode],
) -> tuple[Product, PriceQuote]:
    assert isinstance(result, Ok)
    return result.value


def test_get_product_quotes_with_active_promotion() -> None:
    repo = FakeCatalogRepository(
        (product(id=1, price="1000"),),
        (),
        (
            promo(id=1, product_id=1, percent="10", active=False),
            promo(id=2, product_id=1, percent="20"),
        ),
    )
    item, quote = found(GetProduct(repo)(1))
    assert item.id == 1
    assert quote.final == m("800")
    assert quote.promotion is not None
    assert quote.promotion.id == 2
    assert quote.pix is None


def test_get_product_without_promotion_has_pix() -> None:
    repo = FakeCatalogRepository((product(id=1, price="1000"),))
    _, quote = found(GetProduct(repo)(1))
    assert quote.final == m("1000")
    assert quote.pix == m("950")


def test_get_product_picks_highest_active_percent() -> None:
    repo = FakeCatalogRepository(
        (product(id=1, price="1000"),),
        (),
        (promo(id=1, product_id=1, percent="10"), promo(id=2, product_id=1, percent="15")),
    )
    assert found(GetProduct(repo)(1))[1].final == m("850")


def test_get_product_not_found() -> None:
    assert GetProduct(FakeCatalogRepository())(99) == Err(CatalogErrorCode.PRODUCT_NOT_FOUND)


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
    assert QuoteInstallments()(m("1200")) == Ok(InstallmentPlan(12, m("100")))
    assert QuoteInstallments()(m("1200"), 3) == Ok(InstallmentPlan(3, m("400")))


def test_quote_installments_past_twelve_is_err_installments_not_allowed() -> None:
    assert QuoteInstallments()(m("1200"), 13) == Err(CatalogErrorCode.INSTALLMENTS_NOT_ALLOWED)


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


def test_search_price_ceiling_uses_promotional_final_price() -> None:
    repo = FakeCatalogRepository(
        (product(id=1, name="Violao Crafter", price="2399"),),
        (category(),),
        (promo(id=1, product_id=1, percent="20"),),  # final 1919.20
    )
    found = SearchProducts(repo)("violao", max_price=m("2000"))
    assert isinstance(found, Exact)
    assert found.product.id == 1


def test_search_passes_named_category_and_ceiling() -> None:
    repo = FakeCatalogRepository(
        (product(id=1, name="Violão Giannini", category_id=5, price="900"),),
        (category(id=5, name="Violões"),),
    )

    SearchProducts(repo)("violões até 1000", Money(Decimal(1000)))

    assert repo.searches == [
        ("violões até 1000", CatalogFilter(frozenset({5}), False, Money(Decimal(1000))), 40)
    ]


def test_search_retries_without_category_when_it_finds_nothing() -> None:
    # "cordas" names the category Cordas Orquestrais, but the 7-string guitar is a Violão.
    repo = FakeCatalogRepository(
        (
            product(id=1, name="Violino Eagle", category_id=3),
            product(id=2, name="Shelby SN-7C 7 Cordas Nylon", category_id=5),
        ),
        (category(id=3, name="Cordas Orquestrais"), category(id=5, name="Violões")),
    )

    found = SearchProducts(repo)("7 cordas")

    assert isinstance(found, Exact)
    assert found.product.id == 2
    assert [flt.category_ids for _, flt, _ in repo.searches] == [frozenset({3}), None]
