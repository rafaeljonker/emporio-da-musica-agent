from emporio.catalog.domain.pricing import quote_price
from tests.unit.catalog.factories import m, product, promo


def test_pix_is_five_percent_off_table_without_promotion() -> None:
    q = quote_price(product(price="2199"), None)
    assert q.final == m("2199")
    assert q.pix == m("2089.05")


def test_pix_price_is_absent_when_promotion_active() -> None:
    q = quote_price(product(price="2399"), promo(percent="18", active=True))
    assert q.final == m("1967.18")
    assert q.pix is None


def test_inactive_promotion_is_ignored() -> None:
    q = quote_price(product(price="2399"), promo(percent="18", active=False))
    assert q.final == m("2399")
    assert q.promotion is None
