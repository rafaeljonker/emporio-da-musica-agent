import pytest

from emporio.catalog.application.create_product import CreateProduct
from emporio.catalog.application.update_product import UpdateProduct
from emporio.catalog.domain.errors import CatalogFull, ProductNotOwned, UnknownCategory
from emporio.catalog.domain.product import ProductDraft, ProductStatus
from tests.unit.catalog.factories import category, m
from tests.unit.catalog.fakes import FakeCatalogRepository, FakeCatalogWriter

REPO = FakeCatalogRepository((), (category(id=5, name="Violões"),))


def draft(*, category_id: int = 5, price: str = "1000") -> ProductDraft:
    return ProductDraft("Violão Teste", category_id, "", m(price), 3, ProductStatus.ACTIVE, ())


def test_create_rejects_unknown_category() -> None:
    writer = FakeCatalogWriter()
    with pytest.raises(UnknownCategory):
        CreateProduct(REPO, writer)("a", draft(category_id=99))
    assert writer.rows == {}


def test_create_stops_at_owner_cap() -> None:
    writer = FakeCatalogWriter()
    create = CreateProduct(REPO, writer, max_per_owner=20)
    for _ in range(20):
        create("a", draft())
    with pytest.raises(CatalogFull):
        create("a", draft())
    assert create("b", draft()).id == 100020  # another login still has room


def test_create_stops_at_total_cap() -> None:
    writer = FakeCatalogWriter()
    create = CreateProduct(REPO, writer, max_per_owner=20, max_total=3)
    for owner in ("a", "b", "c"):
        create(owner, draft())
    with pytest.raises(CatalogFull):
        create("d", draft())


def test_update_missing_or_foreign_is_not_owned() -> None:
    writer = FakeCatalogWriter()
    mine = CreateProduct(REPO, writer)("a", draft())
    update = UpdateProduct(REPO, writer)
    with pytest.raises(ProductNotOwned):
        update("b", mine.id, draft(price="1"))
    with pytest.raises(ProductNotOwned):
        update("a", 95, draft(price="1"))
    assert writer.rows[mine.id][1].price == m("1000")
    assert update("a", mine.id, draft(price="900")).price == m("900")


def test_update_rejects_unknown_category() -> None:
    writer = FakeCatalogWriter()
    mine = CreateProduct(REPO, writer)("a", draft())
    with pytest.raises(UnknownCategory):
        UpdateProduct(REPO, writer)("a", mine.id, draft(category_id=99))
