from emporio.catalog.application.ports import CatalogRepository, CatalogWriter
from emporio.catalog.domain.errors import ProductNotOwned, UnknownCategory
from emporio.catalog.domain.product import Product, ProductDraft


class UpdateProduct:
    def __init__(self, repo: CatalogRepository, writer: CatalogWriter) -> None:
        self._repo = repo
        self._writer = writer

    def __call__(self, owner: str, product_id: int, draft: ProductDraft) -> Product:
        if draft.category_id not in {c.id for c in self._repo.categories()}:
            raise UnknownCategory(draft.category_id)
        updated = self._writer.update(owner, product_id, draft)
        if updated is None:
            raise ProductNotOwned(product_id)
        return updated
