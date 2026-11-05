from emporio.catalog.domain.product import ProductStatus
from tests.unit.catalog.factories import product


def test_available_when_active_with_stock() -> None:
    assert product(stock=1).is_available


def test_unavailable_when_out_of_stock() -> None:
    assert not product(stock=0).is_available


def test_unavailable_when_discontinued_even_with_stock() -> None:
    assert not product(stock=13, status=ProductStatus.DISCONTINUED).is_available


def test_coming_soon_is_unavailable() -> None:
    assert not product(stock=2, status=ProductStatus.COMING_SOON).is_available
