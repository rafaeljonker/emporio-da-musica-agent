import csv
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from decimal import InvalidOperation
from functools import cached_property
from pathlib import Path

from emporio.orders.domain.order import Customer, Order, OrderItem, OrderStatus
from emporio.paths import CASE_CSV_FILES
from emporio.shared.errors import DomainError
from emporio.shared.money import Money


class OrdersDataError(DomainError):
    """Raised when an orders CSV row cannot be parsed."""

    def __init__(self, file: str, row: int, cause: Exception) -> None:
        super().__init__(f"{file}, row {row}: {type(cause).__name__}")


def _customer(row: dict[str, str]) -> Customer:
    return Customer(
        id=int(row["customer_id"]),
        name=row["name"],
        phone=row["phone"],
        email=row["email"],
        city=row["city"],
    )


def _item(row: dict[str, str]) -> tuple[int, OrderItem]:
    return int(row["order_id"]), OrderItem(
        product_id=int(row["product_id"]), quantity=int(row["quantity"])
    )


def _order(row: dict[str, str], items: tuple[OrderItem, ...]) -> Order:
    return Order(
        id=int(row["order_id"]),
        customer_id=int(row["customer_id"]),
        order_date=date.fromisoformat(row["order_date"]),
        status=OrderStatus(row["status"]),
        total=Money.from_str(row["total_brl"]),
        payment_method=row["payment_method"],
        tracking_code=row["tracking_code"].strip() or None,
        estimated_delivery=(
            date.fromisoformat(row["estimated_delivery"])
            if row["estimated_delivery"].strip()
            else None
        ),
        notes=row["notes"].strip() or None,
        items=items,
    )


def _load[T](path: Path, parse: Callable[[dict[str, str]], T]) -> tuple[T, ...]:
    items: list[T] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for number, row in enumerate(csv.DictReader(handle), start=2):
            # DictReader pads short rows with None and puts extras under a None key.
            if None in row or None in row.values():
                raise OrdersDataError(path.name, number, ValueError("missing or extra columns"))
            try:
                items.append(parse(row))
            except (ValueError, TypeError, KeyError, InvalidOperation, DomainError) as exc:
                raise OrdersDataError(path.name, number, exc) from exc
    return tuple(items)


class CsvCustomerRepository:
    """Read-only customers loaded lazily from the case CSV."""

    def __init__(self, files: Mapping[str, Path] = CASE_CSV_FILES) -> None:
        self._files = files

    @cached_property
    def _customers(self) -> dict[int, Customer]:
        return {c.id: c for c in _load(self._files["customers"], _customer)}

    def by_id(self, customer_id: int) -> Customer | None:
        return self._customers.get(customer_id)


class CsvOrderRepository:
    """Read-only orders (with items joined) loaded lazily from the case CSVs."""

    def __init__(self, files: Mapping[str, Path] = CASE_CSV_FILES) -> None:
        self._files = files

    @cached_property
    def _orders(self) -> dict[int, Order]:
        items: dict[int, list[OrderItem]] = {}
        for order_id, item in _load(self._files["order_items"], _item):
            items.setdefault(order_id, []).append(item)
        return {
            o.id: o
            for o in _load(
                self._files["orders"],
                lambda row: _order(row, tuple(items.get(int(row["order_id"]), ()))),
            )
        }

    def by_id(self, order_id: int) -> Order | None:
        return self._orders.get(order_id)

    def by_customer(self, customer_id: int) -> Sequence[Order]:
        return tuple(o for o in self._orders.values() if o.customer_id == customer_id)
