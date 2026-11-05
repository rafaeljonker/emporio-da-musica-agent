from collections.abc import Sequence
from typing import Protocol

from emporio.catalog.domain.pricing import Promotion
from emporio.catalog.domain.product import Category, Product


class CatalogRepository(Protocol):
    def products(self) -> Sequence[Product]: ...

    def categories(self) -> Sequence[Category]: ...

    def promotions(self) -> Sequence[Promotion]: ...
