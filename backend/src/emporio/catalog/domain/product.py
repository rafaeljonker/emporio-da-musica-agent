import re
import unicodedata
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


# Matched on lowercase text without accents: "50% OFF", "20 off", promoção, desconto, cupom...
_PROMO_CLAIM = re.compile(
    r"(\d\s*%?|%)\s*off\b|\bpromo(\b|c)|\bdesconto|\bblack\s*friday|\bliquidac|\bcupo(m|ns)\b"
)


def claims_a_promotion(text: str) -> bool:
    """True when the text announces a discount; only promotion rows may carry one."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c)).lower()
    return _PROMO_CLAIM.search(plain) is not None
