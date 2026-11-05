from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

# Docker images may need the `tzdata` package for ZoneInfo (phase 6).
STORE_TZ = ZoneInfo("America/Campo_Grande")
DEFAULT_STORE_TODAY = date(2026, 2, 20)


class Clock(Protocol):
    def today(self) -> date: ...


class SystemClock:
    def today(self) -> date:
        return datetime.now(STORE_TZ).date()


@dataclass(frozen=True)
class FixedClock:
    fixed: date

    def today(self) -> date:
        return self.fixed
