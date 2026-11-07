from collections.abc import Sequence
from dataclasses import replace
from decimal import Decimal

from emporio.catalog.application.admin import CatalogAdminService, ProductInput, ProductView
from emporio.catalog.application.create_product import CreateProduct
from emporio.catalog.application.update_product import UpdateProduct
from emporio.catalog.domain.errors import CatalogErrorCode
from emporio.catalog.domain.product import Product
from emporio.shared.errors import StoreUnavailable
from emporio.shared.result import Err, Ok, Result
from tests.unit.catalog.factories import category
from tests.unit.catalog.fakes import FakeCatalogRepository, FakeCatalogWriter

DATA = ProductInput("Cavaquinho", 5, "", Decimal("10"), 1, "active", (("b", "2"), ("a", "1")))


class DownWriter(FakeCatalogWriter):
    def own(self, owner: str) -> Sequence[Product]:
        raise StoreUnavailable


def _service(writer: FakeCatalogWriter) -> CatalogAdminService:
    repo = FakeCatalogRepository((), (category(id=5, name="Violões"),))
    return CatalogAdminService(
        repo, writer, CreateProduct(repo, writer), UpdateProduct(repo, writer)
    )


def _ok(result: Result[ProductView, CatalogErrorCode]) -> ProductView:
    assert isinstance(result, Ok)
    return result.value


def test_unreachable_database_is_catalog_unavailable() -> None:
    service = _service(DownWriter())
    unavailable = Err(CatalogErrorCode.CATALOG_UNAVAILABLE)
    assert (service.create("a", DATA), service.mine("a")) == (unavailable, unavailable)


def test_domain_errors_map_to_codes() -> None:
    service = _service(FakeCatalogWriter())
    unknown = service.create("a", ProductInput("X", 99, "", Decimal(1), 1, "active", ()))
    foreign = service.update("b", _ok(service.create("a", DATA)).id, DATA)
    assert (unknown, foreign) == (
        Err(CatalogErrorCode.UNKNOWN_CATEGORY),
        Err(CatalogErrorCode.PRODUCT_NOT_OWNED),
    )


def test_store_name_maps_to_name_taken_by_store() -> None:
    service = _service(FakeCatalogWriter(seed_names=("Cavaquinho",)))
    assert service.create("a", DATA) == Err(CatalogErrorCode.NAME_TAKEN_BY_STORE)


def test_promotion_claim_maps_to_promo_claim() -> None:
    result = _service(FakeCatalogWriter()).create("a", replace(DATA, name="Cavaquinho 50% OFF"))
    assert result == Err(CatalogErrorCode.PROMO_CLAIM)


def test_written_product_specs_are_sorted_like_the_stored_row() -> None:
    assert _ok(_service(FakeCatalogWriter()).create("a", DATA)).specs == (("a", "1"), ("b", "2"))
