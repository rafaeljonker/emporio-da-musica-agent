import pytest

from emporio.catalog.application.create_product import CreateProduct
from emporio.catalog.application.update_product import UpdateProduct
from emporio.catalog.domain.errors import CatalogErrorCode
from emporio.catalog.domain.product import Product, ProductDraft, ProductStatus
from emporio.shared.result import Err, Ok, Result
from tests.catalog.fakes import FakeCatalogRepository, FakeCatalogWriter, category, m

REPO = FakeCatalogRepository((), (category(id=5, name="Violões"),))


SEED = "Violão Takamine GD20 Dreadnought Natural"

UNKNOWN_CATEGORY = Err(CatalogErrorCode.UNKNOWN_CATEGORY)
CATALOG_FULL = Err(CatalogErrorCode.CATALOG_FULL)
NOT_OWNED = Err(CatalogErrorCode.PRODUCT_NOT_OWNED)
NAME_TAKEN = Err(CatalogErrorCode.NAME_TAKEN_BY_STORE)
PROMO_CLAIM = Err(CatalogErrorCode.PROMO_CLAIM)


def ok(result: Result[Product, CatalogErrorCode]) -> Product:
    assert isinstance(result, Ok)
    return result.value


def draft(
    *,
    name: str = "Violão Teste",
    description: str = "",
    category_id: int = 5,
    price: str = "1000",
) -> ProductDraft:
    return ProductDraft(name, category_id, description, m(price), 3, ProductStatus.ACTIVE, ())


def test_create_rejects_unknown_category() -> None:
    writer = FakeCatalogWriter()
    assert CreateProduct(REPO, writer)("a", draft(category_id=99)) == UNKNOWN_CATEGORY
    assert writer.rows == {}


def test_create_stops_at_owner_cap() -> None:
    writer = FakeCatalogWriter()
    create = CreateProduct(REPO, writer, max_per_owner=20)
    for _ in range(20):
        create("a", draft())
    assert create("a", draft()) == CATALOG_FULL
    assert ok(create("b", draft())).id == 100020  # another login still has room


def test_create_stops_at_total_cap() -> None:
    writer = FakeCatalogWriter()
    create = CreateProduct(REPO, writer, max_per_owner=20, max_total=3)
    for owner in ("a", "b", "c"):
        create(owner, draft())
    assert create("d", draft()) == CATALOG_FULL


def test_update_missing_or_foreign_is_not_owned() -> None:
    writer = FakeCatalogWriter()
    mine = ok(CreateProduct(REPO, writer)("a", draft()))
    update = UpdateProduct(REPO, writer)
    assert update("b", mine.id, draft(price="1")) == NOT_OWNED
    assert update("a", 95, draft(price="1")) == NOT_OWNED
    assert writer.rows[mine.id][1].price == m("1000")
    assert ok(update("a", mine.id, draft(price="900"))).price == m("900")


def test_update_rejects_unknown_category() -> None:
    writer = FakeCatalogWriter()
    mine = ok(CreateProduct(REPO, writer)("a", draft()))
    assert UpdateProduct(REPO, writer)("a", mine.id, draft(category_id=99)) == UNKNOWN_CATEGORY


def test_create_rejects_a_store_product_name_ignoring_case_and_accents() -> None:
    writer = FakeCatalogWriter(seed_names=(SEED,))
    assert (
        CreateProduct(REPO, writer)("a", draft(name="VIOLAO takamine gd20 dreadnought natural"))
        == NAME_TAKEN
    )
    assert writer.rows == {}


def test_update_rejects_a_store_product_name() -> None:
    writer = FakeCatalogWriter(seed_names=(SEED,))
    mine = ok(CreateProduct(REPO, writer)("a", draft()))
    assert UpdateProduct(REPO, writer)("a", mine.id, draft(name=SEED, price="99")) == NAME_TAKEN
    assert writer.rows[mine.id][1].price == m("1000")


def test_own_name_and_another_demo_name_stay_allowed() -> None:
    writer = FakeCatalogWriter(seed_names=(SEED,))
    mine = ok(CreateProduct(REPO, writer)("a", draft(name="Violão Rozini")))
    assert ok(CreateProduct(REPO, writer)("b", draft(name="violão rozini"))).name == "violão rozini"
    edited = ok(UpdateProduct(REPO, writer)("a", mine.id, draft(name="Violão Rozini", price="9")))
    assert edited.price == m("9")


PROMO_CLAIMS = [
    "Guitarra Strinberg 50% OFF",
    "Pedal 30%off",
    "Baixo 20 off só hoje",
    "Violão em PROMOÇÃO",
    "violao promocao relampago",
    "Teclado Promo",
    "Teclado com Desconto",
    "Ukulele Black Friday",
    "ukulele blackfriday",
    "Liquidação de cordas",
    "Use o CUPOM ROCK10",
]


@pytest.mark.parametrize("text", PROMO_CLAIMS)
def test_create_rejects_a_promotion_claim_in_the_name(text: str) -> None:
    writer = FakeCatalogWriter()
    assert CreateProduct(REPO, writer)("a", draft(name=text)) == PROMO_CLAIM
    assert writer.rows == {}


@pytest.mark.parametrize("text", ["Leve agora com 40 % off", "Últimas peças: liquidação!"])
def test_create_rejects_a_promotion_claim_in_the_description(text: str) -> None:
    assert CreateProduct(REPO, FakeCatalogWriter())("a", draft(description=text)) == PROMO_CLAIM


def test_update_rejects_a_promotion_claim() -> None:
    writer = FakeCatalogWriter()
    mine = ok(CreateProduct(REPO, writer)("a", draft()))
    assert (
        UpdateProduct(REPO, writer)("a", mine.id, draft(description="Desconto de 10%"))
        == PROMO_CLAIM
    )


@pytest.mark.parametrize(
    "name", ["Pedal Overdrive Classic", "Pedal Offset Fuzz", "Cabo 10 metros Official"]
)
def test_plain_product_names_pass(name: str) -> None:
    assert ok(CreateProduct(REPO, FakeCatalogWriter())("a", draft(name=name))).name == name
