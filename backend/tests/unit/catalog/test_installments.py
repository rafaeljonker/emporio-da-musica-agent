from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from emporio.catalog.domain.errors import CatalogErrorCode
from emporio.catalog.domain.installments import (
    InstallmentPlan,
    installment_plan,
    max_installments,
    minimum_for,
)
from emporio.shared.money import Money
from emporio.shared.result import Err, Ok
from tests.unit.catalog.factories import m


def test_900_allows_9_installments_of_100() -> None:
    assert max_installments(m("900")) == InstallmentPlan(9, m("100"))


def test_90_allows_only_one_installment() -> None:
    assert max_installments(m("90")).count == 1


def test_150_allows_three_of_50() -> None:
    assert max_installments(m("150")) == InstallmentPlan(3, m("50"))


def test_twelve_installments_of_2199() -> None:
    assert installment_plan(m("2199"), 12) == Ok(InstallmentPlan(12, m("183.25")))


@pytest.mark.parametrize(
    ("total", "count", "parcel"),
    [("99.99", 1, "99.99"), ("799.99", 7, "114.28"), ("100", 2, "50"), ("800", 8, "100")],
)
def test_minimum_is_checked_on_exact_parcel(total: str, count: int, parcel: str) -> None:
    assert max_installments(m(total)) == InstallmentPlan(count, m(parcel))


NOT_ALLOWED = Err(CatalogErrorCode.INSTALLMENTS_NOT_ALLOWED)


def test_rejects_13_installments() -> None:
    assert installment_plan(m("5000"), 13) == NOT_ALLOWED


def test_rejects_parcel_below_minimum() -> None:
    assert installment_plan(m("90"), 2) == NOT_ALLOWED


@pytest.mark.parametrize("count", [0, -1])
def test_rejects_count_below_one(count: int) -> None:
    assert installment_plan(m("5000"), count) == NOT_ALLOWED


@pytest.mark.parametrize(
    ("count", "minimum"),
    [(1, 0), (2, 50), (3, 50), (4, 80), (6, 80), (7, 100), (12, 100), (0, None), (13, None)],
)
def test_minimum_for_tiers(count: int, minimum: int | None) -> None:
    assert minimum_for(count) == (None if minimum is None else Money(Decimal(minimum)))


@given(st.decimals(min_value=1, max_value=50000, places=2))
def test_max_installments_respects_minimum(total: Decimal) -> None:
    plan = max_installments(Money(total))
    minimum = minimum_for(plan.count)
    assert minimum is not None
    assert plan.count == 1 or total / plan.count >= minimum.amount
