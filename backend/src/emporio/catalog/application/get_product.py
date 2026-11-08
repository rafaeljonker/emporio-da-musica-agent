from emporio.catalog.application.ports import CatalogRepository
from emporio.catalog.domain.errors import CatalogErrorCode
from emporio.catalog.domain.pricing import PriceQuote, best_active_promotion, quote_price
from emporio.catalog.domain.product import Product
from emporio.shared.result import Err, Ok, Result


class GetProduct:
    def __init__(self, repo: CatalogRepository) -> None:
        self._repo = repo

    def __call__(self, product_id: int) -> Result[tuple[Product, PriceQuote], CatalogErrorCode]:
        found = self._repo.get(product_id)
        if found is None:
            return Err(CatalogErrorCode.PRODUCT_NOT_FOUND)
        active = best_active_promotion(self._repo.promotions_for([product_id]))
        return Ok((found, quote_price(found, active)))
