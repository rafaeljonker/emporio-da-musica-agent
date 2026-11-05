import csv
import json
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from functools import cached_property
from pathlib import Path

from emporio.catalog.domain.pricing import Promotion
from emporio.catalog.domain.product import Category, Product, ProductStatus
from emporio.paths import CASE_CSV_FILES
from emporio.shared.errors import DomainError
from emporio.shared.money import Money


class CatalogDataError(DomainError):
    """Raised when a catalog CSV row cannot be parsed."""

    def __init__(self, file: str, row: int, cause: Exception) -> None:
        super().__init__(f"{file}, row {row}: {cause!r}")


def _specs(raw: str) -> tuple[tuple[str, str], ...]:
    if not raw.strip():
        return ()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError(data)
    return tuple(sorted((str(k), str(v)) for k, v in data.items()))  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]


def _product(row: dict[str, str]) -> Product:
    return Product(
        id=int(row["product_id"]),
        name=row["name"],
        category_id=int(row["category_id"]),
        description=row["description"],
        price=Money.from_str(row["price_brl"]),
        stock=int(row["stock_quantity"]),
        status=ProductStatus(row["status"]),
        specs=_specs(row["specs"]),
    )


def _promotion(row: dict[str, str]) -> Promotion:
    return Promotion(
        id=int(row["promotion_id"]),
        product_id=int(row["product_id"]),
        percent=Decimal(row["discount_percent"]),
        label=row["description"],
        active=row["is_active"].strip() == "1",
    )


def _category(row: dict[str, str]) -> Category:
    return Category(id=int(row["category_id"]), name=row["name"], description=row["description"])


class CsvCatalogRepository:
    """Read-only catalog loaded lazily, once per file, from the case CSVs."""

    def __init__(self, files: Mapping[str, Path] = CASE_CSV_FILES) -> None:
        self._files = files

    def _load[T](self, key: str, parse: Callable[[dict[str, str]], T]) -> tuple[T, ...]:
        path = self._files[key]
        items: list[T] = []
        with path.open(encoding="utf-8", newline="") as handle:
            for number, row in enumerate(csv.DictReader(handle), start=2):
                # DictReader pads short rows with None and puts extras under a None key.
                if None in row or None in row.values():
                    exc = ValueError("missing or extra columns")
                    raise CatalogDataError(path.name, number, exc)
                try:
                    items.append(parse(row))
                except (ValueError, TypeError, KeyError, InvalidOperation, DomainError) as exc:
                    raise CatalogDataError(path.name, number, exc) from exc
        return tuple(items)

    @cached_property
    def _products(self) -> tuple[Product, ...]:
        return self._load("products", _product)

    @cached_property
    def _categories(self) -> tuple[Category, ...]:
        return self._load("categories", _category)

    @cached_property
    def _promotions(self) -> tuple[Promotion, ...]:
        return self._load("promotions", _promotion)

    def products(self) -> Sequence[Product]:
        return self._products

    def categories(self) -> Sequence[Category]:
        return self._categories

    def promotions(self) -> Sequence[Promotion]:
        return self._promotions
