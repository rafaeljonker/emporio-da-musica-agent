from collections import defaultdict

from emporio.catalog.application.ports import CatalogRepository
from emporio.catalog.domain.pricing import PriceQuote, Promotion, best_active_promotion, quote_price
from emporio.catalog.domain.product import Product


class ListPromotions:
    def __init__(self, repo: CatalogRepository) -> None:
        self._repo = repo

    def __call__(self) -> tuple[tuple[Product, PriceQuote], ...]:
        products = self._repo.promoted()
        groups: defaultdict[int, list[Promotion]] = defaultdict(list)
        for promo in self._repo.promotions_for([p.id for p in products]):
            groups[promo.product_id].append(promo)
        items: list[tuple[Product, PriceQuote]] = []
        for product in products:
            best = best_active_promotion(groups[product.id])
            if best is not None:
                items.append((product, quote_price(product, best)))
        return tuple(sorted(items, key=lambda item: item[0].name))
