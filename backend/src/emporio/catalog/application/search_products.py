from collections import defaultdict

from emporio.catalog.application.ports import CatalogRepository
from emporio.catalog.domain.pricing import Promotion, best_active_promotion, quote_price
from emporio.catalog.domain.search import SearchResult, search_products
from emporio.shared.money import Money


class SearchProducts:
    def __init__(self, repo: CatalogRepository) -> None:
        self._repo = repo

    def __call__(
        self, query: str, max_price: Money | None = None, include_unavailable: bool = False
    ) -> SearchResult:
        products = self._repo.products()
        if max_price is not None:
            # The ceiling is what the customer pays, so promotions count.
            groups: defaultdict[int, list[Promotion]] = defaultdict(list)
            for promo in self._repo.promotions():
                groups[promo.product_id].append(promo)
            products = [
                p
                for p in products
                if quote_price(p, best_active_promotion(groups.get(p.id, ()))).final <= max_price
            ]
        return search_products(
            products, self._repo.categories(), query, include_unavailable=include_unavailable
        )
