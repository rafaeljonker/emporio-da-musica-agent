from emporio.catalog.application.ports import CatalogRepository, CatalogWriter
from emporio.catalog.domain.errors import CatalogErrorCode
from emporio.catalog.domain.product import Product, ProductDraft, claims_a_promotion
from emporio.shared.result import Err, Ok, Result


def check_draft(
    repo: CatalogRepository, writer: CatalogWriter, draft: ProductDraft
) -> CatalogErrorCode | None:
    """The write rules a create and an update share."""
    if draft.category_id not in {c.id for c in repo.categories()}:
        return CatalogErrorCode.UNKNOWN_CATEGORY
    if claims_a_promotion(draft.name) or claims_a_promotion(draft.description):
        return CatalogErrorCode.PROMO_CLAIM
    # A twin of a store product at a fake price would sit next to the real one in every search.
    if writer.seed_name_taken(draft.name):
        return CatalogErrorCode.NAME_TAKEN_BY_STORE
    return None


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

    def __call__(self, owner: str, draft: ProductDraft) -> Result[Product, CatalogErrorCode]:
        if rejected := check_draft(self._repo, self._writer, draft):
            return Err(rejected)
        # ponytail: caps are checked then written without a lock; two racing creates can pass
        # one over the cap, fine for a demo
        if (
            len(self._writer.own(owner)) >= self._max_per_owner
            or self._writer.admin_total() >= self._max_total
        ):
            return Err(CatalogErrorCode.CATALOG_FULL)
        return Ok(self._writer.create(owner, draft))
