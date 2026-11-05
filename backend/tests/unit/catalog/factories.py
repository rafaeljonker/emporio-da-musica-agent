from decimal import Decimal

from emporio.catalog.domain.pricing import Promotion
from emporio.catalog.domain.product import Category, Product, ProductStatus
from emporio.shared.money import Money


def m(value: str) -> Money:
    return Money.from_str(value)


def product(
    *,
    id: int = 1,
    name: str = "Violao",
    category_id: int = 1,
    description: str = "",
    price: str = "1000",
    stock: int = 5,
    status: ProductStatus = ProductStatus.ACTIVE,
    specs: tuple[tuple[str, str], ...] = (),
) -> Product:
    return Product(id, name, category_id, description, m(price), stock, status, specs)


def promo(
    *,
    id: int = 1,
    product_id: int = 1,
    percent: str = "10",
    label: str = "Promo",
    active: bool = True,
) -> Promotion:
    return Promotion(id, product_id, Decimal(percent), label, active)


def category(*, id: int = 1, name: str = "Violoes", description: str = "") -> Category:
    return Category(id, name, description)
