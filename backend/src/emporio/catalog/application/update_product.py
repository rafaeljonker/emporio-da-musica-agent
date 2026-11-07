from emporio.catalog.application.create_product import check_draft
from emporio.catalog.application.ports import CatalogRepository, CatalogWriter
from emporio.catalog.domain.errors import ProductNotOwned
from emporio.catalog.domain.product import Product, ProductDraft


class UpdateProduct:
    def __init__(self, repo: CatalogRepository, writer: CatalogWriter) -> None:
        self._repo = repo
        self._writer = writer

    def __call__(self, owner: str, product_id: int, draft: ProductDraft) -> Product:
        check_draft(self._repo, self._writer, draft)
        updated = self._writer.update(owner, product_id, draft)
        if updated is None:
            raise ProductNotOwned(product_id)
        return updated
