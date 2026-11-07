from collections.abc import Sequence
from dataclasses import replace
from decimal import Decimal

import pytest

from emporio.catalog.application.create_product import CreateProduct
from emporio.catalog.application.update_product import UpdateProduct
from emporio.catalog.domain.product import Product
from emporio.db import IndexUnavailable
from emporio.support.application.ports import CatalogWriteRejected, ProductInput
from emporio.support.infrastructure.catalog_admin import CatalogAdminService
from tests.unit.catalog.factories import category
from tests.unit.catalog.fakes import FakeCatalogRepository, FakeCatalogWriter

DATA = ProductInput("Cavaquinho", 5, "", Decimal("10"), 1, "active", (("b", "2"), ("a", "1")))


class DownWriter(FakeCatalogWriter):
    def own(self, owner: str) -> Sequence[Product]:
        raise IndexUnavailable


def _service(writer: FakeCatalogWriter) -> CatalogAdminService:
    repo = FakeCatalogRepository((), (category(id=5, name="Violões"),))
    return CatalogAdminService(
        repo, writer, CreateProduct(repo, writer), UpdateProduct(repo, writer)
    )


def test_unreachable_database_is_catalog_unavailable() -> None:
    service = _service(DownWriter())
    for call in (lambda: service.create("a", DATA), lambda: service.mine("a")):
        with pytest.raises(CatalogWriteRejected) as err:
            call()
        assert err.value.code == "catalog_unavailable"


def test_domain_errors_map_to_codes() -> None:
    service = _service(FakeCatalogWriter())
    with pytest.raises(CatalogWriteRejected) as unknown:
        service.create("a", ProductInput("X", 99, "", Decimal(1), 1, "active", ()))
    with pytest.raises(CatalogWriteRejected) as foreign:
        service.update("b", service.create("a", DATA).id, DATA)
    assert (unknown.value.code, foreign.value.code) == ("unknown_category", "not_found")


def test_store_name_maps_to_name_taken_by_store() -> None:
    service = _service(FakeCatalogWriter(seed_names=("Cavaquinho",)))
    with pytest.raises(CatalogWriteRejected) as err:
        service.create("a", DATA)
    assert err.value.code == "name_taken_by_store"


def test_promotion_claim_maps_to_promo_claim() -> None:
    with pytest.raises(CatalogWriteRejected) as err:
        _service(FakeCatalogWriter()).create("a", replace(DATA, name="Cavaquinho 50% OFF"))
    assert err.value.code == "promo_claim"


def test_written_product_specs_are_sorted_like_the_stored_row() -> None:
    assert _service(FakeCatalogWriter()).create("a", DATA).specs == (("a", "1"), ("b", "2"))
