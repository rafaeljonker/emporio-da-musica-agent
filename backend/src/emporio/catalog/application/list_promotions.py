from emporio.catalog.application.ports import CatalogRepository
from emporio.catalog.domain.pricing import PriceQuote, Promotion, quote_price
from emporio.catalog.domain.product import Product


class ListPromotions:
    def __init__(self, repo: CatalogRepository) -> None:
        self._repo = repo

    def __call__(self) -> tuple[tuple[Product, PriceQuote], ...]:
        by_id = {p.id: p for p in self._repo.products()}
        best: dict[int, Promotion] = {}
        for promo in self._repo.promotions():
            current = best.get(promo.product_id)
            if promo.active and (current is None or promo.percent > current.percent):
                best[promo.product_id] = promo
        items = [
            (by_id[pid], quote_price(by_id[pid], promo))
            for pid, promo in best.items()
            if pid in by_id and by_id[pid].is_available
        ]
        return tuple(sorted(items, key=lambda item: item[0].name))
