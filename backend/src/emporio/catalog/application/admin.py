"""The web layer's door to catalog writes: primitive DTOs in, catalog drafts and views out."""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from emporio.catalog.application.create_product import CreateProduct
from emporio.catalog.application.ports import CatalogRepository, CatalogWriter
from emporio.catalog.application.update_product import UpdateProduct
from emporio.catalog.domain.errors import CatalogErrorCode
from emporio.catalog.domain.product import Product, ProductDraft, ProductStatus
from emporio.shared.errors import StoreUnavailable
from emporio.shared.money import Money
from emporio.shared.result import Err, Ok, Result


@dataclass(frozen=True)
class ProductInput:
    """One product as a demo user submits it (primitives only: no catalog types here)."""

    name: str
    category_id: int
    description: str
    price: Decimal
    stock: int
    status: str
    specs: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ProductView:
    id: int
    name: str
    category_id: int
    category: str
    description: str
    price: Decimal
    stock: int
    status: str
    specs: tuple[tuple[str, str], ...]


class CatalogAdmin(Protocol):
    """What the web layer may do to the catalog: demo users create and edit their own rows."""

    def categories(self) -> Result[tuple[tuple[int, str], ...], CatalogErrorCode]: ...

    def create(self, owner: str, data: ProductInput) -> Result[ProductView, CatalogErrorCode]: ...

    def update(
        self, owner: str, product_id: int, data: ProductInput
    ) -> Result[ProductView, CatalogErrorCode]: ...

    def mine(self, owner: str) -> Result[tuple[ProductView, ...], CatalogErrorCode]:
        """Newest first."""
        ...


def _available[T](read: Callable[[], Result[T, CatalogErrorCode]]) -> Result[T, CatalogErrorCode]:
    """The one place an unreachable database becomes a code the web layer can answer with."""
    try:
        return read()
    except StoreUnavailable:
        return Err(CatalogErrorCode.CATALOG_UNAVAILABLE)


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

    def categories(self) -> Result[tuple[tuple[int, str], ...], CatalogErrorCode]:
        return _available(lambda: Ok(self._categories()))

    def create(self, owner: str, data: ProductInput) -> Result[ProductView, CatalogErrorCode]:
        return _available(lambda: self._viewed(self._create(owner, _draft(data))))

    def update(
        self, owner: str, product_id: int, data: ProductInput
    ) -> Result[ProductView, CatalogErrorCode]:
        return _available(lambda: self._viewed(self._update(owner, product_id, _draft(data))))

    def mine(self, owner: str) -> Result[tuple[ProductView, ...], CatalogErrorCode]:
        return _available(lambda: Ok(tuple(self._view(p) for p in self._writer.own(owner))))

    def _categories(self) -> tuple[tuple[int, str], ...]:
        return tuple((c.id, c.name) for c in self._repo.categories())

    def _viewed(
        self, written: Result[Product, CatalogErrorCode]
    ) -> Result[ProductView, CatalogErrorCode]:
        match written:
            case Ok(product):
                return Ok(self._view(product))
            case Err() as rejected:
                return rejected

    def _view(self, p: Product) -> ProductView:
        names = dict(self._categories())
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
