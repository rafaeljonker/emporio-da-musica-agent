from emporio.shared.errors import DomainError


class ProductNotFound(DomainError):
    """Raised when a product id does not exist in the catalog."""

    def __init__(self, product_id: int) -> None:
        super().__init__(f"product {product_id} not found")
