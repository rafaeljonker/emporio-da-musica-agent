import unicodedata
from collections.abc import Collection, Sequence
from dataclasses import dataclass, field

from emporio.catalog.application.ports import CatalogFilter
from emporio.catalog.domain.pricing import Promotion, best_active_promotion, quote_price
from emporio.catalog.domain.product import Category, Product, ProductDraft


@dataclass(frozen=True, slots=True)
class FakeCatalogRepository:
    """In-memory port. `search` ignores the query and `k` and returns every product that passes
    the filter, so the domain grader does the ranking; each call is recorded in `searches`."""

    _products: tuple[Product, ...] = ()
    _categories: tuple[Category, ...] = ()
    _promotions: tuple[Promotion, ...] = ()
    searches: list[tuple[str, CatalogFilter, int]] = field(default_factory=list)

    def get(self, product_id: int) -> Product | None:
        return next((p for p in self._products if p.id == product_id), None)

    def get_many(self, ids: Collection[int]) -> Sequence[Product]:
        return tuple(p for p in self._products if p.id in ids)

    def categories(self) -> Sequence[Category]:
        return self._categories

    def promotions_for(self, ids: Collection[int]) -> Sequence[Promotion]:
        return tuple(x for x in self._promotions if x.product_id in ids)

    def promoted(self) -> Sequence[Product]:
        return tuple(
            p
            for p in self._products
            if p.is_available and best_active_promotion(self.promotions_for([p.id])) is not None
        )

    def search(self, query: str, flt: CatalogFilter, k: int) -> Sequence[Product]:
        self.searches.append((query, flt, k))
        return tuple(p for p in self._products if self._passes(p, flt))

    def _passes(self, p: Product, flt: CatalogFilter) -> bool:
        if flt.category_ids is not None and p.category_id not in flt.category_ids:
            return False
        if flt.available_only and not p.is_available:
            return False
        if flt.max_price is None:
            return True
        best = best_active_promotion(self.promotions_for([p.id]))
        return quote_price(p, best).final <= flt.max_price


@dataclass(slots=True)
class FakeCatalogWriter:
    """In-memory writer: `rows` maps id to (owner, product); ids start at 100000 like the DB.
    `seed_names` are the store's own product names."""

    rows: dict[int, tuple[str, Product]] = field(default_factory=dict)
    seed_names: tuple[str, ...] = ()

    def seed_name_taken(self, name: str) -> bool:
        return _key(name) in {_key(n) for n in self.seed_names}

    def create(self, owner: str, draft: ProductDraft) -> Product:
        created = draft.with_id(100000 + len(self.rows))
        self.rows[created.id] = (owner, created)
        return created

    def update(self, owner: str, product_id: int, draft: ProductDraft) -> Product | None:
        row = self.rows.get(product_id)
        if row is None or row[0] != owner:
            return None
        self.rows[product_id] = (owner, draft.with_id(product_id))
        return self.rows[product_id][1]

    def own(self, owner: str) -> Sequence[Product]:
        return tuple(p for o, p in reversed(self.rows.values()) if o == owner)

    def admin_total(self) -> int:
        return len(self.rows)


def _key(name: str) -> str:
    """Like the `name_key` column: lowercase, accents stripped."""
    decomposed = unicodedata.normalize("NFKD", name)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()
