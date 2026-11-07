from emporio.catalog.domain.product import ProductStatus
from evals.facts import recommendation_facts
from tests.unit.catalog.factories import category, product

CATEGORIES = (
    category(id=1, name="Guitarras"),
    category(id=2, name="Baixos"),
    category(id=5, name="Violões"),
    category(id=9, name="Ukuleles"),
)
NYLON = (("strings", "nylon"),)


def test_mpb_facts_name_available_nylon_violoes_and_forbid_electric() -> None:
    products = (
        product(id=81, name="Yamaha C40 Nylon Natural", category_id=5, specs=NYLON),
        product(
            id=95, name="Takamine GD20 Dreadnought", category_id=5, specs=(("strings", "steel"),)
        ),
        product(
            id=113,
            name="Shelby SN-7C 7 Cordas Nylon",
            category_id=5,
            specs=NYLON,
            status=ProductStatus.DISCONTINUED,
        ),
        product(id=116, name="Kala KA-15S Soprano", category_id=9, specs=NYLON),
        product(id=134, name="Fender Telecaster Player Series", category_id=1),
        product(id=138, name="Music Man Bass 4X", category_id=2),
    )

    facts = recommendation_facts(products, CATEGORIES)

    assert facts == {
        "nylon_violao_names": ("Yamaha C40",),
        "electric_names": ("Fender Telecaster", "Music Man"),
    }
