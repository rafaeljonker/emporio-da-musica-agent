from emporio.catalog.application.create_product import check_draft
from emporio.catalog.application.ports import CatalogRepository, CatalogWriter
from emporio.catalog.domain.errors import CatalogErrorCode
from emporio.catalog.domain.product import Product, ProductDraft
from emporio.shared.result import Err, Ok, Result


class UpdateProduct:
    def __init__(self, repo: CatalogRepository, writer: CatalogWriter) -> None:
        self._repo = repo
        self._writer = writer

    def __call__(
        self, owner: str, product_id: int, draft: ProductDraft
    ) -> Result[Product, CatalogErrorCode]:
        if rejected := check_draft(self._repo, self._writer, draft):
            return Err(rejected)
        updated = self._writer.update(owner, product_id, draft)
        if updated is None:
            return Err(CatalogErrorCode.PRODUCT_NOT_OWNED)
        return Ok(updated)
