from emporio.catalog.application.ports import CatalogRepository
from emporio.catalog.domain.errors import ProductNotFound
from emporio.catalog.domain.pricing import PriceQuote, best_active_promotion, quote_price
from emporio.catalog.domain.product import Product


class GetProduct:
    def __init__(self, repo: CatalogRepository) -> None:
        self._repo = repo

    def __call__(self, product_id: int) -> tuple[Product, PriceQuote]:
        found = next((p for p in self._repo.products() if p.id == product_id), None)
        if found is None:
            raise ProductNotFound(product_id)
        active = best_active_promotion(
            x for x in self._repo.promotions() if x.product_id == product_id
        )
        return found, quote_price(found, active)
