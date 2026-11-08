from emporio.orders.application.ports import CustomerRepository, OrderRepository
from emporio.orders.domain.errors import OrdersErrorCode
from emporio.orders.domain.identity import matches_identity
from emporio.orders.domain.order import Order
from emporio.shared.result import Err, Ok, Result


class GetOrderStatus:
    def __init__(self, orders: OrderRepository, customers: CustomerRepository) -> None:
        self._orders = orders
        self._customers = customers

    def __call__(self, order_id: int, email_or_phone: str) -> Result[Order, OrdersErrorCode]:
        # Unknown order and wrong identity give the same error: no id enumeration.
        found = self._orders.by_id(order_id)
        if found is None:
            return Err(OrdersErrorCode.ORDER_NOT_FOUND)
        customer = self._customers.by_id(found.customer_id)
        if customer is None or not matches_identity(customer, email_or_phone):
            return Err(OrdersErrorCode.ORDER_NOT_FOUND)
        return Ok(found)
