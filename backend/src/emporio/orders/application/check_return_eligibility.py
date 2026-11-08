from emporio.orders.application.ports import OrderRepository
from emporio.orders.domain.errors import OrdersErrorCode
from emporio.orders.domain.return_policy import ReturnEligibility, check_return
from emporio.shared.clock import Clock
from emporio.shared.result import Err, Ok, Result


class CheckReturnEligibility:
    def __init__(self, orders: OrderRepository, clock: Clock) -> None:
        self._orders = orders
        self._clock = clock

    def __call__(
        self, order_id: int, customer_id: int
    ) -> Result[ReturnEligibility, OrdersErrorCode]:
        found = self._orders.by_id(order_id)
        # Another customer's order looks exactly like an unknown one: no existence leak.
        if found is None or found.customer_id != customer_id:
            return Err(OrdersErrorCode.ORDER_NOT_FOUND)
        return Ok(check_return(found, self._clock.today()))
