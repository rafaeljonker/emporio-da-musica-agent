from emporio.catalog.application.admin import ProductInput, ProductView
from emporio.catalog.domain.errors import CatalogErrorCode
from emporio.shared.result import Err, Ok, Result

_CATEGORIES = ((5, "Violões"), (9, "Ukuleles"))


class FakeCatalogAdmin:
    """A CatalogAdmin that records calls; `reject` (when set) is returned by all but categories."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int | None, ProductInput | None]] = []
        self.reject: CatalogErrorCode | None = None
        self.rows: list[tuple[str, ProductView]] = []

    def categories(self) -> Result[tuple[tuple[int, str], ...], CatalogErrorCode]:
        return Ok(_CATEGORIES)

    def create(self, owner: str, data: ProductInput) -> Result[ProductView, CatalogErrorCode]:
        self.calls.append(("create", owner, None, data))
        if self.reject is not None:
            return Err(self.reject)
        view = _view(100000 + len(self.rows), data)
        self.rows.append((owner, view))
        return Ok(view)

    def update(
        self, owner: str, product_id: int, data: ProductInput
    ) -> Result[ProductView, CatalogErrorCode]:
        self.calls.append(("update", owner, product_id, data))
        if self.reject is not None:
            return Err(self.reject)
        return Ok(_view(product_id, data))

    def mine(self, owner: str) -> Result[tuple[ProductView, ...], CatalogErrorCode]:
        self.calls.append(("mine", owner, None, None))
        if self.reject is not None:
            return Err(self.reject)
        return Ok(tuple(v for o, v in reversed(self.rows) if o == owner))


def _view(product_id: int, data: ProductInput) -> ProductView:
    return ProductView(
        product_id,
        data.name,
        data.category_id,
        dict(_CATEGORIES).get(data.category_id, ""),
        data.description,
        data.price,
        data.stock,
        data.status,
        data.specs,
    )
