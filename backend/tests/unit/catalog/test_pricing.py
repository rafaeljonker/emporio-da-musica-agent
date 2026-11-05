from emporio.catalog.domain.pricing import best_active_promotion, quote_price
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


def test_best_active_promotion_none_when_none_active() -> None:
    assert best_active_promotion([]) is None
    assert best_active_promotion([promo(percent="30", active=False)]) is None


def test_best_active_promotion_ignores_inactive() -> None:
    best = best_active_promotion(
        [promo(id=1, percent="30", active=False), promo(id=2, percent="10")]
    )
    assert best is not None
    assert best.id == 2


def test_best_active_promotion_highest_percent_wins() -> None:
    best = best_active_promotion([promo(id=1, percent="10"), promo(id=2, percent="20")])
    assert best is not None
    assert best.percent == 20


def test_best_active_promotion_tie_lowest_id() -> None:
    best = best_active_promotion([promo(id=7, percent="10"), promo(id=3, percent="10")])
    assert best is not None
    assert best.id == 3
