"""Store-knowledge facts for the golden cases, derived from the catalog data. Pure, no IO."""

from collections.abc import Sequence

from emporio.catalog.domain.product import Category, Product
from emporio.shared.text import fold


def short_name(product: Product) -> str:
    return " ".join(product.name.split()[:2])  # brand + model, as the spike matched names


def _in(products: Sequence[Product], categories: Sequence[Category], *names: str) -> list[Product]:
    ids = {c.id for c in categories if fold(c.name) in {fold(n) for n in names}}
    return [p for p in products if p.category_id in ids]


def recommendation_facts(
    products: Sequence[Product], categories: Sequence[Category]
) -> dict[str, tuple[str, ...]]:
    """MPB at home: any available nylon violão is right; an electric guitar or bass is wrong."""
    nylon = [
        p
        for p in _in(products, categories, "Violões")
        if p.is_available and dict(p.specs).get("strings") == "nylon"
    ]
    electric = _in(products, categories, "Guitarras", "Baixos")
    return {
        "nylon_violao_names": tuple(dict.fromkeys(short_name(p) for p in nylon)),
        "electric_names": tuple(dict.fromkeys(short_name(p) for p in electric)),
    }
