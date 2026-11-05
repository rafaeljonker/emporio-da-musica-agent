from collections.abc import Sequence
from dataclasses import dataclass

from emporio.orders.domain.order import Customer, Order


@dataclass(frozen=True, slots=True)
class FakeOrderRepository:
    _orders: tuple[Order, ...] = ()

    def by_id(self, order_id: int) -> Order | None:
        return next((o for o in self._orders if o.id == order_id), None)

    def by_customer(self, customer_id: int) -> Sequence[Order]:
        return tuple(o for o in self._orders if o.customer_id == customer_id)


@dataclass(frozen=True, slots=True)
class FakeCustomerRepository:
    _customers: tuple[Customer, ...] = ()

    def by_id(self, customer_id: int) -> Customer | None:
        return next((c for c in self._customers if c.id == customer_id), None)
