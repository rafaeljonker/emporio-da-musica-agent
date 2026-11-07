from emporio.catalog.application.ports import CatalogRepository, CatalogWriter
from emporio.catalog.domain.errors import CatalogFull, UnknownCategory
from emporio.catalog.domain.product import Product, ProductDraft


class CreateProduct:
    def __init__(
        self,
        repo: CatalogRepository,
        writer: CatalogWriter,
        max_per_owner: int = 20,
        max_total: int = 500,
    ) -> None:
        self._repo = repo
        self._writer = writer
        self._max_per_owner = max_per_owner
        self._max_total = max_total

    def __call__(self, owner: str, draft: ProductDraft) -> Product:
        if draft.category_id not in {c.id for c in self._repo.categories()}:
            raise UnknownCategory(draft.category_id)
        # ponytail: caps are checked then written without a lock; two racing creates can pass
        # one over the cap, fine for a demo
        if (
            len(self._writer.own(owner)) >= self._max_per_owner
            or self._writer.admin_total() >= self._max_total
        ):
            raise CatalogFull
        return self._writer.create(owner, draft)
