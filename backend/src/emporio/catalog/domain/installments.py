from dataclasses import dataclass
from decimal import Decimal

from emporio.shared.errors import DomainError
from emporio.shared.money import Money

MAX_INSTALLMENTS = 12


class InvalidInstallments(DomainError):
    """Raised when an installment count is out of range or the parcel is too small."""


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


def installment_plan(total: Money, count: int) -> InstallmentPlan:
    parcel = total.divided_by(count) if count >= 1 else None
    if parcel is None or parcel.amount < minimum_for(count):
        raise InvalidInstallments(count)
    return InstallmentPlan(count, parcel)


def max_installments(total: Money) -> InstallmentPlan:
    for count in range(MAX_INSTALLMENTS, 1, -1):
        parcel = total.divided_by(count)
        if parcel.amount >= minimum_for(count):
            return InstallmentPlan(count, parcel)
    return InstallmentPlan(1, total)
