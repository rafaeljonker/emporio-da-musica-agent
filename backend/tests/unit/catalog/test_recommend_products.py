from collections.abc import Mapping, Sequence

import pytest

from emporio.catalog.application.recommend_products import RecommendProducts
from emporio.catalog.domain.product import Product, ProductStatus
from emporio.catalog.domain.search import Candidates, NoMatch
from tests.unit.catalog.factories import product
from tests.unit.catalog.fakes import FakeCatalogRepository


class FakeIndex:
    def __init__(self, ids: Sequence[int]) -> None:
        self.ids = ids
        self.asked: tuple[str, int] | None = None

    def similar(self, need: str, k: int) -> Sequence[int]:
        self.asked = (need, k)
        return self.ids

    def replace_all(self, products: Sequence[Product], category_names: Mapping[int, str]) -> None:
        raise NotImplementedError


def _recommend(ids: Sequence[int], *products: Product) -> RecommendProducts:
    return RecommendProducts(FakeCatalogRepository(products), FakeIndex(ids))


def test_recommend_returns_candidates_in_index_order() -> None:
    a, b, c = product(id=1), product(id=2), product(id=3)

    result = _recommend([3, 1, 2], a, b, c)("quero algo")

    assert result == Candidates((c, a, b))


def test_recommend_skips_unavailable_products() -> None:
    ok = product(id=1)
    gone = product(id=2, status=ProductStatus.DISCONTINUED)
    soon = product(id=3, status=ProductStatus.COMING_SOON)
    empty = product(id=4, stock=0)

    result = _recommend([2, 3, 4, 1], ok, gone, soon, empty)("quero algo")

    assert result == Candidates((ok,))


def test_recommend_never_returns_exact() -> None:
    only = product(id=1)

    assert _recommend([1], only)("quero algo") == Candidates((only,))


def test_recommend_truncates_to_limit_and_asks_for_ten() -> None:
    items = [product(id=i) for i in range(1, 8)]
    index = FakeIndex(range(1, 8))

    result = RecommendProducts(FakeCatalogRepository(tuple(items)), index)("x", limit=3)

    assert result == Candidates(tuple(items[:3]))
    assert index.asked == ("x", 10)


def test_blank_need_is_no_match() -> None:
    assert _recommend([1], product(id=1))("   ") == NoMatch()


def test_no_available_product_is_no_match() -> None:
    assert _recommend([1], product(id=1, stock=0))("x") == NoMatch()


def test_limit_above_pool_asks_index_for_limit() -> None:
    items = [product(id=i) for i in range(1, 13)]
    index = FakeIndex(range(1, 13))

    result = RecommendProducts(FakeCatalogRepository(tuple(items)), index)("x", limit=12)

    assert index.asked == ("x", 12)
    assert result == Candidates(tuple(items))


def test_recommend_skips_ids_missing_from_catalog() -> None:
    a = product(id=1)

    assert _recommend([99, 1], a)("x") == Candidates((a,))


@pytest.mark.parametrize("limit", [0, -1])
def test_recommend_with_non_positive_limit_returns_no_match_without_asking_index(
    limit: int,
) -> None:
    index = FakeIndex([1, 2])
    recommend = RecommendProducts(FakeCatalogRepository([product(id=1), product(id=2)]), index)

    assert recommend("quero algo", limit) == NoMatch()
    assert index.asked is None
