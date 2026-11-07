from datetime import date

from emporio.orders.application.check_return_eligibility import CheckReturnEligibility
from emporio.orders.application.get_order_status import GetOrderStatus
from emporio.orders.application.list_customer_orders import ListCustomerOrders
from emporio.orders.domain.errors import OrdersErrorCode
from emporio.orders.domain.return_policy import ReturnEligibility, ReturnReason
from emporio.shared.clock import FixedClock
from emporio.shared.result import Err, Ok
from tests.unit.orders.factories import cust, order
from tests.unit.orders.fakes import FakeCustomerRepository, FakeOrderRepository

PEDRO = cust()
OTHER = cust(id=2, phone="(67) 91111-2222", email="ana@jmail.com")
NOT_FOUND = Err(OrdersErrorCode.ORDER_NOT_FOUND)


def _status() -> GetOrderStatus:
    orders = FakeOrderRepository((order(id=10, customer_id=1), order(id=11, customer_id=2)))
    return GetOrderStatus(orders, FakeCustomerRepository((PEDRO, OTHER)))


def test_get_order_status_returns_order_for_matching_identity() -> None:
    found = _status()(10, "pedro.oliveira@jmail.com")
    assert isinstance(found, Ok)
    assert found.value.id == 10


def test_get_order_status_rejects_other_customers_order() -> None:
    assert _status()(11, "pedro.oliveira@jmail.com") == NOT_FOUND


def test_get_order_status_rejects_wrong_identity() -> None:
    assert _status()(10, "ana@jmail.com") == NOT_FOUND


def test_unknown_order_and_wrong_identity_are_indistinguishable() -> None:
    unknown = _status()(999, "pedro.oliveira@jmail.com")
    wrong = _status()(10, "ana@jmail.com")
    assert unknown == wrong == NOT_FOUND


def test_list_customer_orders_newest_first() -> None:
    old = order(id=1, order_date=date(2026, 1, 1))
    new = order(id=2, order_date=date(2026, 2, 1))
    result = ListCustomerOrders(FakeOrderRepository((old, new)))(1)
    assert [o.id for o in result] == [2, 1]


def test_return_eligibility_hides_other_customers_order_as_not_found() -> None:
    use_case = CheckReturnEligibility(
        FakeOrderRepository((order(id=10, customer_id=1),)), FixedClock(date(2026, 2, 12))
    )
    assert use_case(10, 2) == NOT_FOUND


def test_return_eligibility_is_not_found_for_unknown_order() -> None:
    use_case = CheckReturnEligibility(FakeOrderRepository(), FixedClock(date(2026, 2, 12)))
    assert use_case(10, 1) == NOT_FOUND


def test_return_eligibility_uses_injected_clock() -> None:
    orders = FakeOrderRepository((order(id=10, customer_id=1),))
    early = CheckReturnEligibility(orders, FixedClock(date(2026, 2, 12)))(10, 1)
    late = CheckReturnEligibility(orders, FixedClock(date(2026, 6, 1)))(10, 1)
    assert early == Ok(
        ReturnEligibility(
            True,
            True,
            date(2026, 2, 10),
            date(2026, 2, 17),
            date(2026, 3, 3),
            ReturnReason.WITHIN_REGRET_WINDOW,
        )
    )
    assert late == Ok(
        ReturnEligibility(
            False,
            False,
            date(2026, 2, 10),
            date(2026, 2, 17),
            date(2026, 3, 3),
            ReturnReason.DEFECT_WINDOW_CLOSED,
        )
    )
