from collections.abc import Sequence
from typing import Protocol

from emporio.orders.domain.order import Customer, Order


class OrderRepository(Protocol):
    def by_id(self, order_id: int) -> Order | None: ...

    def by_customer(self, customer_id: int) -> Sequence[Order]: ...


class CustomerRepository(Protocol):
    def by_id(self, customer_id: int) -> Customer | None: ...
