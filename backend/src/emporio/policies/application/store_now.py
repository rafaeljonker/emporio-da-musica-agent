from dataclasses import dataclass
from datetime import date, datetime

from emporio.policies.domain.store_hours import is_open, next_opening
from emporio.shared.clock import Clock


@dataclass(frozen=True, slots=True)
class StoreStatus:
    open: bool
    now: datetime
    next_opening: datetime


@dataclass(frozen=True, slots=True)
class StoreNow:
    clock: Clock
    holidays: frozenset[date]

    def __call__(self) -> StoreStatus:
        now = self.clock.now()
        return StoreStatus(
            open=is_open(now, self.holidays),
            now=now,
            next_opening=next_opening(now, self.holidays),
        )
