from dataclasses import dataclass
from decimal import Decimal

from emporio.shared.errors import DomainError
from emporio.shared.money import Money

MAX_INSTALLMENTS = 12


class InvalidInstallments(DomainError):
    """Raised when an installment count is out of range or the parcel is too small."""

    def __init__(self, count: int, total: Money | None = None) -> None:
        suffix = "" if total is None else f" for total {total.amount}"
        super().__init__(f"{count} installments not allowed{suffix}")


@dataclass(frozen=True, slots=True)
class InstallmentPlan:
    count: int
    parcel: Money


def minimum_for(count: int) -> Decimal:
    if count == 1:
        return Decimal(0)
    if 2 <= count <= 3:
        return Decimal(50)
    if 4 <= count <= 6:
        return Decimal(80)
    if 7 <= count <= MAX_INSTALLMENTS:
        return Decimal(100)
    raise InvalidInstallments(count)


def _allowed(total: Money, count: int) -> bool:
    # Exact (unrounded) parcel: rounding up must never let the sum exceed the total.
    return total.amount / count >= minimum_for(count)


def installment_plan(total: Money, count: int) -> InstallmentPlan:
    if count < 1 or count > MAX_INSTALLMENTS or not _allowed(total, count):
        raise InvalidInstallments(count, total)
    return InstallmentPlan(count, total.divided_by(count))


def max_installments(total: Money) -> InstallmentPlan:
    for count in range(MAX_INSTALLMENTS, 1, -1):
        if _allowed(total, count):
            return InstallmentPlan(count, total.divided_by(count))
    return InstallmentPlan(1, total)
