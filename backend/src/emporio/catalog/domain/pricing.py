from dataclasses import dataclass
from decimal import Decimal

from emporio.catalog.domain.product import Product
from emporio.shared.money import Money

PIX_DISCOUNT = Decimal(5)


@dataclass(frozen=True, slots=True)
class Promotion:
    id: int
    product_id: int
    percent: Decimal
    label: str
    active: bool


@dataclass(frozen=True, slots=True)
class PriceQuote:
    table: Money
    promotion: Promotion | None
    final: Money
    pix: Money | None


def quote_price(product: Product, promotion: Promotion | None) -> PriceQuote:
    table = product.price
    if promotion is not None and promotion.active:
        return PriceQuote(table, promotion, table.percent_off(promotion.percent), None)
    return PriceQuote(table, None, table, table.percent_off(PIX_DISCOUNT))
