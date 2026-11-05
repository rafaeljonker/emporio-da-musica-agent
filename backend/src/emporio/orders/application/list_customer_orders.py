from emporio.orders.application.ports import OrderRepository
from emporio.orders.domain.order import Order


class ListCustomerOrders:
    def __init__(self, orders: OrderRepository) -> None:
        self._orders = orders

    def __call__(self, customer_id: int) -> tuple[Order, ...]:
        return tuple(
            sorted(self._orders.by_customer(customer_id), key=lambda o: o.order_date, reverse=True)
        )
