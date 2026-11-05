from emporio.orders.application.ports import CustomerRepository, OrderRepository
from emporio.orders.domain.identity import IdentityMismatch, matches_identity
from emporio.orders.domain.order import Order


class GetOrderStatus:
    def __init__(self, orders: OrderRepository, customers: CustomerRepository) -> None:
        self._orders = orders
        self._customers = customers

    def __call__(self, order_id: int, email_or_phone: str) -> Order:
        # Unknown order and wrong identity raise the same error: no id enumeration.
        found = self._orders.by_id(order_id)
        if found is None:
            raise IdentityMismatch
        customer = self._customers.by_id(found.customer_id)
        if customer is None or not matches_identity(customer, email_or_phone):
            raise IdentityMismatch
        return found
