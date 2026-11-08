from datetime import date

import pytest

from emporio.orders.application.check_return_eligibility import CheckReturnEligibility
from emporio.orders.application.get_order_status import GetOrderStatus
from emporio.orders.application.list_customer_orders import ListCustomerOrders
from emporio.orders.domain.errors import OrdersErrorCode
from emporio.orders.domain.order import OrderStatus
from emporio.orders.domain.return_policy import ReturnEligibility, ReturnReason
from emporio.orders.infrastructure.csv_order_repository import (
    CsvCustomerRepository,
    CsvOrderRepository,
)
from emporio.shared.clock import FixedClock
from emporio.shared.result import Err, Ok

pytestmark = pytest.mark.files

repo = CsvOrderRepository()
customers = CsvCustomerRepository()
clock = FixedClock(date(2026, 2, 20))


def eligibility(order_id: int, customer_id: int) -> ReturnEligibility:
    result = CheckReturnEligibility(repo, clock)(order_id, customer_id)
    assert isinstance(result, Ok)
    return result.value


def test_order_7_is_regret_eligible() -> None:
    assert eligibility(7, 14).regret_eligible


def test_order_5_is_not_regret_eligible() -> None:
    assert not eligibility(5, 5).regret_eligible


def test_cancelled_order_17_is_not_eligible() -> None:
    r = eligibility(17, 15)
    assert not r.regret_eligible
    assert not r.defect_eligible


def test_order_6_defect_window_closed_on_feb_20() -> None:
    r = eligibility(6, 9)
    assert not r.regret_eligible
    assert not r.defect_eligible
    assert r.reason is ReturnReason.DEFECT_WINDOW_CLOSED


def test_order_5_status_with_owner_email() -> None:
    order = GetOrderStatus(repo, customers)(5, "rafael.pereira@jmail.com")
    assert isinstance(order, Ok)
    assert order.value.status is OrderStatus.DELIVERED


def test_order_5_with_other_customers_email_is_rejected() -> None:
    result = GetOrderStatus(repo, customers)(5, "joao.silva@gmail.com")
    assert result == Err(OrdersErrorCode.ORDER_NOT_FOUND)


def test_customer_3_has_two_orders_newest_first() -> None:
    orders = ListCustomerOrders(repo)(3)
    assert len(orders) == 2
    assert orders[0].order_date > orders[1].order_date


def test_empty_tracking_and_delivery_map_to_none() -> None:
    order = repo.by_id(17)
    assert order is not None
    assert order.tracking_code is None
    assert order.estimated_delivery is None


def test_items_are_joined() -> None:
    order = repo.by_id(1)
    assert order is not None
    assert [(i.product_id, i.quantity) for i in order.items] == [(93, 1)]
