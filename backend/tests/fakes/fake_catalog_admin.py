from emporio.support.application.ports import (
    CatalogWriteRejected,
    ProductInput,
    ProductView,
    RejectionCode,
)


class FakeCatalogAdmin:
    """A CatalogAdmin that records calls; `reject` (when set) is raised by all but categories."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int | None, ProductInput | None]] = []
        self.reject: RejectionCode | None = None
        self.rows: list[tuple[str, ProductView]] = []

    def categories(self) -> tuple[tuple[int, str], ...]:
        return ((5, "Violões"), (9, "Ukuleles"))

    def create(self, owner: str, data: ProductInput) -> ProductView:
        self.calls.append(("create", owner, None, data))
        if self.reject is not None:
            raise CatalogWriteRejected(self.reject)
        view = _view(100000 + len(self.rows), data)
        self.rows.append((owner, view))
        return view

    def update(self, owner: str, product_id: int, data: ProductInput) -> ProductView:
        self.calls.append(("update", owner, product_id, data))
        if self.reject is not None:
            raise CatalogWriteRejected(self.reject)
        return _view(product_id, data)

    def mine(self, owner: str) -> tuple[ProductView, ...]:
        self.calls.append(("mine", owner, None, None))
        if self.reject is not None:
            raise CatalogWriteRejected(self.reject)
        return tuple(v for o, v in reversed(self.rows) if o == owner)


def _view(product_id: int, data: ProductInput) -> ProductView:
    return ProductView(
        product_id,
        data.name,
        data.category_id,
        dict(FakeCatalogAdmin().categories()).get(data.category_id, ""),
        data.description,
        data.price,
        data.stock,
        data.status,
        data.specs,
    )
