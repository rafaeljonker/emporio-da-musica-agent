from emporio.shared.errors import DomainError


class OrderNotFound(DomainError):
    """Raised when an order id does not exist."""

    def __init__(self, order_id: int) -> None:
        super().__init__(f"order {order_id} not found")
