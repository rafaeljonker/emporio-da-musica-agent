import pytest

from emporio.catalog.application.ports import CatalogFilter
from emporio.catalog.application.recommend_products import RecommendProducts
from emporio.catalog.domain.product import Product, ProductStatus
from emporio.catalog.domain.search import Candidates, NoMatch
from tests.catalog.fakes import FakeCatalogRepository, product


def _recommend(*products: Product) -> RecommendProducts:
    return RecommendProducts(FakeCatalogRepository(products))


def test_recommend_returns_candidates_in_search_order() -> None:
    a, b, c = product(id=1), product(id=2), product(id=3)

    result = _recommend(c, a, b)("quero algo")

    assert result == Candidates((c, a, b))


def test_recommend_skips_unavailable_products() -> None:
    ok = product(id=1)
    gone = product(id=2, status=ProductStatus.DISCONTINUED)
    soon = product(id=3, status=ProductStatus.COMING_SOON)
    empty = product(id=4, stock=0)

    result = _recommend(gone, soon, empty, ok)("quero algo")

    assert result == Candidates((ok,))


def test_recommend_never_returns_exact() -> None:
    only = product(id=1)

    assert _recommend(only)("quero algo") == Candidates((only,))


def test_recommend_truncates_to_limit() -> None:
    items = [product(id=i) for i in range(1, 8)]

    result = _recommend(*items)("x", limit=3)

    assert result == Candidates(tuple(items[:3]))


def test_recommend_asks_only_available_with_limit() -> None:
    repo = FakeCatalogRepository((product(id=1),))

    RecommendProducts(repo)("x", limit=3)
    empty = RecommendProducts(FakeCatalogRepository((product(id=1, stock=0),)))("x", limit=3)

    assert repo.searches == [("x", CatalogFilter(available_only=True), 3)]
    assert empty == NoMatch()


def test_blank_need_is_no_match() -> None:
    assert _recommend(product(id=1))("   ") == NoMatch()


def test_no_available_product_is_no_match() -> None:
    assert _recommend(product(id=1, stock=0))("x") == NoMatch()


@pytest.mark.parametrize("limit", [0, -1])
def test_recommend_with_non_positive_limit_returns_no_match_without_searching(
    limit: int,
) -> None:
    repo = FakeCatalogRepository((product(id=1), product(id=2)))

    assert RecommendProducts(repo)("quero algo", limit) == NoMatch()
    assert repo.searches == []
