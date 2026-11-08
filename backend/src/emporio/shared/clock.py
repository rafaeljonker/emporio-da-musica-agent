from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Protocol
from zoneinfo import ZoneInfo

# Docker images may need the `tzdata` package for ZoneInfo (phase 6).
STORE_TZ = ZoneInfo("America/Campo_Grande")
DEFAULT_STORE_TODAY = date(2026, 2, 20)


class Clock(Protocol):
    def today(self) -> date: ...
    def now(self) -> datetime: ...


@dataclass(frozen=True)
class FixedClock:
    fixed: date
    at: time = time(12, 0)

    def today(self) -> date:
        return self.fixed

    def now(self) -> datetime:
        return datetime.combine(self.fixed, self.at, tzinfo=STORE_TZ)
