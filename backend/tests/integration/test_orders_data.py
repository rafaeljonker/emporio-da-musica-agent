from datetime import date

import pytest

from emporio.orders.application.check_return_eligibility import CheckReturnEligibility
from emporio.orders.application.get_order_status import GetOrderStatus
from emporio.orders.application.list_customer_orders import ListCustomerOrders
from emporio.orders.domain.identity import IdentityMismatch
from emporio.orders.domain.order import OrderStatus
from emporio.orders.infrastructure.csv_order_repository import CsvOrderRepository
from emporio.shared.clock import FixedClock

repo = CsvOrderRepository()
clock = FixedClock(date(2026, 2, 20))


def test_order_7_is_regret_eligible() -> None:
    assert CheckReturnEligibility(repo, clock)(7, 14).regret_eligible


def test_order_5_is_not_regret_eligible() -> None:
    assert not CheckReturnEligibility(repo, clock)(5, 5).regret_eligible


def test_cancelled_order_17_is_not_eligible() -> None:
    r = CheckReturnEligibility(repo, clock)(17, 15)
    assert not r.regret_eligible
    assert not r.defect_eligible


def test_order_5_status_with_owner_email() -> None:
    order = GetOrderStatus(repo, repo)(5, "rafael.pereira@jmail.com")
    assert order.status is OrderStatus.DELIVERED


def test_order_5_with_other_customers_email_is_rejected() -> None:
    with pytest.raises(IdentityMismatch):
        GetOrderStatus(repo, repo)(5, "joao.silva@gmail.com")


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
