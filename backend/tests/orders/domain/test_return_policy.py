from datetime import date, timedelta

import pytest

from emporio.orders.domain.order import OrderStatus
from emporio.orders.domain.return_policy import ReturnReason, check_return
from tests.orders.fakes import order

TODAY = date(2026, 2, 20)


def test_regret_within_seven_days_of_delivery():
    e = check_return(
        order(status=OrderStatus.DELIVERED, estimated_delivery=date(2026, 2, 17)), TODAY
    )
    assert e.regret_eligible
    assert e.regret_deadline == date(2026, 2, 24)
    assert e.delivered_on == date(2026, 2, 17)
    assert e.reason == ReturnReason.WITHIN_REGRET_WINDOW


def test_regret_deadline_day_is_inclusive():
    e = check_return(order(estimated_delivery=date(2026, 2, 13)), TODAY)
    assert e.regret_deadline == TODAY
    assert e.regret_eligible


def test_regret_closed_after_seven_days():
    e = check_return(order(estimated_delivery=date(2026, 1, 18)), TODAY)
    assert not e.regret_eligible


def test_cancelled_order_is_not_eligible():
    e = check_return(order(status=OrderStatus.CANCELLED, estimated_delivery=None), TODAY)
    assert not e.regret_eligible
    assert not e.defect_eligible
    assert e.reason == ReturnReason.CANCELLED


def test_shipped_order_is_not_yet_eligible():
    e = check_return(order(status=OrderStatus.SHIPPED), TODAY)
    assert e.reason == ReturnReason.NOT_DELIVERED
    assert not e.regret_eligible
    assert not e.defect_eligible


def test_defect_within_thirty_days_of_purchase():
    e = check_return(
        order(
            status=OrderStatus.DELIVERED,
            order_date=date(2026, 2, 3),
            estimated_delivery=date(2026, 2, 17),
        ),
        TODAY,
    )
    assert e.defect_eligible
    assert e.defect_deadline == date(2026, 3, 5)


def test_defect_window_only_after_regret_window_closed():
    e = check_return(
        order(order_date=date(2026, 1, 25), estimated_delivery=date(2026, 2, 1)), TODAY
    )
    assert not e.regret_eligible
    assert e.defect_eligible
    assert e.reason == ReturnReason.WITHIN_DEFECT_WINDOW


def test_both_windows_closed():
    e = check_return(order(order_date=date(2026, 1, 1), estimated_delivery=date(2026, 1, 5)), TODAY)
    assert not e.regret_eligible
    assert not e.defect_eligible
    assert e.reason == ReturnReason.DEFECT_WINDOW_CLOSED


def test_delivered_without_delivery_date_has_no_regret_window():
    e = check_return(order(order_date=date(2026, 2, 10), estimated_delivery=None), TODAY)
    assert not e.regret_eligible
    assert e.regret_deadline is None
    assert e.defect_eligible
    assert e.reason == ReturnReason.NO_DELIVERY_DATE


@pytest.mark.parametrize(
    ("days_after_order", "defect_eligible", "reason"),
    [
        (30, True, ReturnReason.WITHIN_DEFECT_WINDOW),
        (31, False, ReturnReason.DEFECT_WINDOW_CLOSED),
    ],
)
def test_defect_window_boundary_is_day_30_after_order_date(
    days_after_order: int, defect_eligible: bool, reason: ReturnReason
):
    order_date = date(2026, 1, 1)
    e = check_return(
        order(order_date=order_date, estimated_delivery=date(2026, 1, 2)),
        order_date + timedelta(days=days_after_order),
    )
    assert e.defect_eligible is defect_eligible
    assert e.reason == reason
