from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Self

from emporio.shared.errors import DomainError

_CENT = Decimal("0.01")
_HUNDRED = Decimal(100)


class InvalidMoney(DomainError):
    """Raised for unparseable amounts or invalid money operations."""


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", self.amount.quantize(_CENT, rounding=ROUND_HALF_UP))

    @classmethod
    def from_str(cls, value: str) -> Self:
        try:
            amount = Decimal(value)
        except InvalidOperation as exc:
            raise InvalidMoney(value) from exc
        if not amount.is_finite():
            raise InvalidMoney(value)
        return cls(amount)

    def percent_off(self, percent: Decimal) -> Self:
        return type(self)(self.amount * (_HUNDRED - percent) / _HUNDRED)

    def divided_by(self, parts: int) -> Self:
        if parts < 1:
            raise InvalidMoney(parts)
        return type(self)(self.amount / parts)

    def format_brl(self) -> str:
        """Voice format: "R$ 2.199" for whole values, "R$ 2.089,05" with cents."""
        text = format_brl(self)
        return text.removesuffix(",00")

    def __add__(self, other: Self) -> Self:
        return type(self)(self.amount + other.amount)

    def __lt__(self, other: Self) -> bool:
        return self.amount < other.amount

    def __le__(self, other: Self) -> bool:
        return self.amount <= other.amount


def format_brl(money: Money) -> str:
    us = f"{money.amount:,.2f}"  # 1,967.18
    return "R$ " + us.replace(",", "_").replace(".", ",").replace("_", ".")
