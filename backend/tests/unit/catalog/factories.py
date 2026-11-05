from typing import Any

from emporio.catalog.domain.product import Product, ProductStatus
from emporio.shared.money import Money


def m(value: str) -> Money:
    return Money.from_str(value)


def product(**overrides: Any) -> Product:  # noqa: ANN401
    fields: dict[str, Any] = {
        "id": 1,
        "name": "Violao",
        "category_id": 1,
        "description": "",
        "price": "1000",
        "stock": 5,
        "status": ProductStatus.ACTIVE,
        "specs": (),
    }
    fields.update(overrides)
    if isinstance(fields["price"], str):
        fields["price"] = m(fields["price"])
    return Product(**fields)
