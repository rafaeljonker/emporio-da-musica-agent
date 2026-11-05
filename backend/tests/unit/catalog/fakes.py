from collections.abc import Sequence
from dataclasses import dataclass

from emporio.catalog.domain.pricing import Promotion
from emporio.catalog.domain.product import Category, Product


@dataclass(frozen=True, slots=True)
class FakeCatalogRepository:
    _products: tuple[Product, ...] = ()
    _categories: tuple[Category, ...] = ()
    _promotions: tuple[Promotion, ...] = ()

    def products(self) -> Sequence[Product]:
        return self._products

    def categories(self) -> Sequence[Category]:
        return self._categories

    def promotions(self) -> Sequence[Promotion]:
        return self._promotions
