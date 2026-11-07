from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import Protocol

from emporio.catalog.domain.pricing import Promotion
from emporio.catalog.domain.product import Category, Product, ProductDraft
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


class CatalogWriter(Protocol):
    """Demo-user writes; only `source='admin'` rows owned by `owner` are ever touched."""

    def create(self, owner: str, draft: ProductDraft) -> Product: ...

    def update(self, owner: str, product_id: int, draft: ProductDraft) -> Product | None:
        """None when the row is missing, a seed row or another owner's."""
        ...

    def own(self, owner: str) -> Sequence[Product]:
        """Newest first."""
        ...

    def admin_total(self) -> int: ...

    def seed_name_taken(self, name: str) -> bool:
        """True when a store (seed) product has this name, case and accents ignored."""
        ...
