from dataclasses import dataclass
from decimal import Decimal

from emporio.catalog.domain.errors import CatalogErrorCode
from emporio.shared.money import Money
from emporio.shared.result import Err, Ok, Result

MAX_INSTALLMENTS = 12


@dataclass(frozen=True, slots=True)
class InstallmentPlan:
    count: int
    parcel: Money


def minimum_for(count: int) -> Money | None:
    """The smallest parcel allowed for `count` installments; None when the count is out of range."""
    if count == 1:
        return Money(Decimal(0))
    if 2 <= count <= 3:
        return Money(Decimal(50))
    if 4 <= count <= 6:
        return Money(Decimal(80))
    if 7 <= count <= MAX_INSTALLMENTS:
        return Money(Decimal(100))
    return None


def _allowed(total: Money, count: int) -> bool:
    minimum = minimum_for(count)
    # Exact (unrounded) parcel: rounding up must never let the sum exceed the total.
    return minimum is not None and total.amount / count >= minimum.amount


def installment_plan(total: Money, count: int) -> Result[InstallmentPlan, CatalogErrorCode]:
    if not _allowed(total, count):
        return Err(CatalogErrorCode.INSTALLMENTS_NOT_ALLOWED)
    return Ok(InstallmentPlan(count, total.divided_by(count)))


def max_installments(total: Money) -> InstallmentPlan:
    for count in range(MAX_INSTALLMENTS, 1, -1):
        if _allowed(total, count):
            return InstallmentPlan(count, total.divided_by(count))
    return InstallmentPlan(1, total)
