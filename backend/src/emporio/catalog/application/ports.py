from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import Protocol

from emporio.catalog.domain.pricing import Promotion
from emporio.catalog.domain.product import Category, Product
from emporio.shared.money import Money


@dataclass(frozen=True, slots=True)
class CatalogFilter:
    category_ids: frozenset[int] | None = None
    available_only: bool = False
    max_price: Money | None = None  # the final price after the best active promotion


class CatalogRepository(Protocol):
    def get(self, product_id: int) -> Product | None: ...

    def get_many(self, ids: Collection[int]) -> Sequence[Product]:
        """Any order; unknown ids are skipped."""
        ...

    def categories(self) -> Sequence[Category]: ...

    def promotions_for(self, ids: Collection[int]) -> Sequence[Promotion]:
        """Active and inactive promotions of these products."""
        ...

    def promoted(self) -> Sequence[Product]:
        """Available products with an active promotion."""
        ...

    def search(self, query: str, flt: CatalogFilter, k: int) -> Sequence[Product]:
        """At most `k` products passing `flt`, best first."""
        ...
