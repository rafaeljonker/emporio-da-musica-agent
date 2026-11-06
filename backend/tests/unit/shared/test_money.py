from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from emporio.shared.errors import DomainError
from emporio.shared.money import Money, format_brl


def test_from_str_quantizes_half_up():
    assert Money.from_str("599.9").amount == Decimal("599.90")


def test_percent_off_rounds_half_up():
    assert Money.from_str("2399").percent_off(Decimal(18)) == Money.from_str("1967.18")


def test_pix_style_discount():
    assert Money.from_str("2199").percent_off(Decimal(5)) == Money.from_str("2089.05")


def test_format_brl_uses_dot_thousands_and_comma_decimals():
    assert format_brl(Money.from_str("1967.18")) == "R$ 1.967,18"


def test_format_brl_small_value():
    assert format_brl(Money.from_str("0.05")) == "R$ 0,05"


def test_from_str_rejects_garbage():
    with pytest.raises(DomainError):
        Money.from_str("abc")


@given(
    st.decimals(min_value=0, max_value=100000, places=2),
    st.integers(min_value=0, max_value=100),
)
def test_percent_off_never_exceeds_original(value: Decimal, pct: int):
    assert Money(value).percent_off(Decimal(pct)) <= Money(value)


def test_money_method_format_brl_drops_zero_cents():
    assert Money.from_str("2199").format_brl() == "R$ 2.199"


def test_money_method_format_brl_keeps_cents():
    assert Money.from_str("2089.05").format_brl() == "R$ 2.089,05"
