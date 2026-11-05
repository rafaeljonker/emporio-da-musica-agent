from collections.abc import Mapping, Sequence
from typing import Protocol

from emporio.catalog.domain.pricing import Promotion
from emporio.catalog.domain.product import Category, Product


class CatalogRepository(Protocol):
    def products(self) -> Sequence[Product]: ...

    def categories(self) -> Sequence[Category]: ...

    def promotions(self) -> Sequence[Promotion]: ...


class ProductIndex(Protocol):
    def similar(self, need: str, k: int) -> Sequence[int]:
        """Product ids, most similar to the need first."""
        ...

    def replace_all(
        self, products: Sequence[Product], category_names: Mapping[int, str]
    ) -> None: ...
