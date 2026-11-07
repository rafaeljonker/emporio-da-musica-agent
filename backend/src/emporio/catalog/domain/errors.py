from emporio.shared.errors import DomainError


class ProductNotFound(DomainError):
    """Raised when a product id does not exist in the catalog."""

    def __init__(self, product_id: int) -> None:
        super().__init__(f"product {product_id} not found")


class UnknownCategory(DomainError):
    def __init__(self, category_id: int) -> None:
        super().__init__(f"category {category_id} not found")


class ProductNotOwned(DomainError):
    """Missing, seed or another login's product; callers cannot tell them apart."""

    def __init__(self, product_id: int) -> None:
        super().__init__(f"product {product_id} not editable")


class CatalogFull(DomainError):
    def __init__(self) -> None:
        super().__init__("catalog write cap reached")


class NameTakenByStore(DomainError):
    """A demo product may not reuse a store product's name (case and accents ignored)."""

    def __init__(self) -> None:
        super().__init__("name taken by a store product")


class PromoClaim(DomainError):
    """Name or description claims a discount; only promotion rows carry one."""

    def __init__(self) -> None:
        super().__init__("promotion claim in product text")
