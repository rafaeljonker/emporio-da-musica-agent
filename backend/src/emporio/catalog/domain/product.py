from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from emporio.shared.money import Money


class ProductStatus(StrEnum):
    ACTIVE = "active"
    DISCONTINUED = "discontinued"
    COMING_SOON = "coming_soon"


@dataclass(frozen=True, slots=True)
class Category:
    id: int
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class Product:
    id: int
    name: str
    category_id: int
    description: str
    price: Money
    stock: int
    status: ProductStatus
    specs: tuple[tuple[str, str], ...]

    @property
    def is_available(self) -> bool:
        return self.status is ProductStatus.ACTIVE and self.stock > 0


def search_document(
    name: str, category: str, description: str, specs: Sequence[tuple[str, str]]
) -> str:
    """The text a product is found by (full text and embedding)."""
    joined = "; ".join(f"{k}: {v}" for k, v in specs)
    return f"{name}. {category}. {description} {joined}".strip()


@dataclass(frozen=True, slots=True)
class ProductDraft:
    """A product as a demo user submits it; the store assigns the id."""

    name: str
    category_id: int
    description: str
    price: Money
    stock: int
    status: ProductStatus
    specs: tuple[tuple[str, str], ...]

    def with_id(self, product_id: int) -> Product:
        return Product(
            product_id,
            self.name,
            self.category_id,
            self.description,
            self.price,
            self.stock,
            self.status,
            self.specs,
        )
