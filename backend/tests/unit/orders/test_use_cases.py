from datetime import date

import pytest

from emporio.orders.application.check_return_eligibility import CheckReturnEligibility
from emporio.orders.application.get_order_status import GetOrderStatus
from emporio.orders.application.list_customer_orders import ListCustomerOrders
from emporio.orders.domain.errors import OrderNotFound
from emporio.orders.domain.identity import IdentityMismatch
from emporio.orders.domain.return_policy import ReturnEligibility
from emporio.shared.clock import FixedClock
from tests.unit.orders.factories import cust, order
from tests.unit.orders.fakes import FakeCustomerRepository, FakeOrderRepository

PEDRO = cust()
OTHER = cust(id=2, phone="(67) 91111-2222", email="ana@jmail.com")


def _status() -> GetOrderStatus:
    orders = FakeOrderRepository((order(id=10, customer_id=1), order(id=11, customer_id=2)))
    return GetOrderStatus(orders, FakeCustomerRepository((PEDRO, OTHER)))


def test_get_order_status_returns_order_for_matching_identity() -> None:
    assert _status()(10, "pedro.oliveira@jmail.com").id == 10


def test_get_order_status_rejects_other_customers_order() -> None:
    with pytest.raises(IdentityMismatch):
        _status()(11, "pedro.oliveira@jmail.com")


def test_get_order_status_rejects_wrong_identity() -> None:
    with pytest.raises(IdentityMismatch):
        _status()(10, "ana@jmail.com")


def test_unknown_order_and_wrong_identity_are_indistinguishable() -> None:
    with pytest.raises(IdentityMismatch) as unknown:
        _status()(999, "pedro.oliveira@jmail.com")
    with pytest.raises(IdentityMismatch) as wrong:
        _status()(10, "ana@jmail.com")
    assert str(unknown.value) == str(wrong.value)


def test_list_customer_orders_newest_first() -> None:
    old = order(id=1, order_date=date(2026, 1, 1))
    new = order(id=2, order_date=date(2026, 2, 1))
    result = ListCustomerOrders(FakeOrderRepository((old, new)))(1)
    assert [o.id for o in result] == [2, 1]


def test_return_eligibility_hides_other_customers_order_as_not_found() -> None:
    use_case = CheckReturnEligibility(
        FakeOrderRepository((order(id=10, customer_id=1),)), FixedClock(date(2026, 2, 12))
    )
    with pytest.raises(OrderNotFound):
        use_case(10, 2)


def test_return_eligibility_raises_not_found_for_unknown_order() -> None:
    use_case = CheckReturnEligibility(FakeOrderRepository(), FixedClock(date(2026, 2, 12)))
    with pytest.raises(OrderNotFound):
        use_case(10, 1)


def test_return_eligibility_uses_injected_clock() -> None:
    orders = FakeOrderRepository((order(id=10, customer_id=1),))
    early = CheckReturnEligibility(orders, FixedClock(date(2026, 2, 12)))(10, 1)
    late = CheckReturnEligibility(orders, FixedClock(date(2026, 6, 1)))(10, 1)
    assert early == ReturnEligibility(
        True,
        True,
        date(2026, 2, 10),
        date(2026, 2, 17),
        date(2026, 3, 3),
        "within_regret_window",
    )
    assert late == ReturnEligibility(
        False,
        False,
        date(2026, 2, 10),
        date(2026, 2, 17),
        date(2026, 3, 3),
        "defect_window_closed",
    )
