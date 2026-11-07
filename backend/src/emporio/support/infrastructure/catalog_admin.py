"""The web layer's door to catalog writes: maps primitive DTOs to catalog drafts and back."""

from collections.abc import Iterator
from contextlib import contextmanager

from emporio.catalog.application.create_product import CreateProduct
from emporio.catalog.application.ports import CatalogRepository, CatalogWriter
from emporio.catalog.application.update_product import UpdateProduct
from emporio.catalog.domain.errors import CatalogFull, ProductNotOwned, UnknownCategory
from emporio.catalog.domain.product import Product, ProductDraft, ProductStatus
from emporio.db import IndexUnavailable
from emporio.shared.money import Money
from emporio.support.application.ports import CatalogWriteRejected, ProductInput, ProductView


@contextmanager
def _rejections() -> Iterator[None]:
    try:
        yield
    except UnknownCategory as err:
        raise CatalogWriteRejected("unknown_category") from err
    except ProductNotOwned as err:
        raise CatalogWriteRejected("not_found") from err
    except CatalogFull as err:
        raise CatalogWriteRejected("catalog_full") from err
    except IndexUnavailable as err:
        raise CatalogWriteRejected("catalog_unavailable") from err


class CatalogAdminService:
    def __init__(
        self,
        repo: CatalogRepository,
        writer: CatalogWriter,
        create: CreateProduct,
        update: UpdateProduct,
    ) -> None:
        self._repo = repo
        self._writer = writer
        self._create = create
        self._update = update

    def categories(self) -> tuple[tuple[int, str], ...]:
        with _rejections():
            return tuple((c.id, c.name) for c in self._repo.categories())

    def create(self, owner: str, data: ProductInput) -> ProductView:
        with _rejections():
            return self._view(self._create(owner, _draft(data)))

    def update(self, owner: str, product_id: int, data: ProductInput) -> ProductView:
        with _rejections():
            return self._view(self._update(owner, product_id, _draft(data)))

    def mine(self, owner: str) -> tuple[ProductView, ...]:
        with _rejections():
            return tuple(self._view(p) for p in self._writer.own(owner))

    def _view(self, p: Product) -> ProductView:
        names = dict(self.categories())
        return ProductView(
            p.id,
            p.name,
            p.category_id,
            names.get(p.category_id, ""),
            p.description,
            p.price.amount,
            p.stock,
            p.status.value,
            tuple(sorted(p.specs)),  # stored rows come back sorted; a fresh write matches them
        )


def _draft(data: ProductInput) -> ProductDraft:
    return ProductDraft(
        data.name,
        data.category_id,
        data.description,
        Money(data.price),
        data.stock,
        ProductStatus(data.status),
        data.specs,
    )
