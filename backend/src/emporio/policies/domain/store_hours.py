from datetime import date, datetime, time, timedelta

from emporio.shared.clock import STORE_TZ
from emporio.shared.errors import DomainError

# Policy section 2. Opening inclusive, closing exclusive. Keys are date.weekday().
WEEKLY_HOURS: dict[int, tuple[time, time] | None] = {
    0: (time(9), time(18)),
    1: (time(9), time(18)),
    2: (time(9), time(18)),
    3: (time(9), time(18)),
    4: (time(9), time(18)),
    5: (time(9), time(13)),
    6: None,
}
MAX_LOOKAHEAD_DAYS = 14


class NaiveDatetimeError(DomainError):
    """A timezone-naive datetime was passed where an aware one is required."""

    def __init__(self) -> None:
        super().__init__("now must be timezone-aware")


class NoOpeningFound(DomainError):
    """No opening within the lookahead window."""

    def __init__(self, since: datetime) -> None:
        super().__init__(f"no opening within {MAX_LOOKAHEAD_DAYS} days of {since}")


def _hours(day: date, holidays: frozenset[date]) -> tuple[time, time] | None:
    return None if day in holidays else WEEKLY_HOURS[day.weekday()]


def _to_store_time(now: datetime) -> datetime:
    if now.tzinfo is None:
        raise NaiveDatetimeError
    return now.astimezone(STORE_TZ)


def is_open(now: datetime, holidays: frozenset[date]) -> bool:
    now = _to_store_time(now)
    hours = _hours(now.date(), holidays)
    return hours is not None and hours[0] <= now.time() < hours[1]


def next_opening(now: datetime, holidays: frozenset[date]) -> datetime:
    """Return `now` when open, else the next opening instant (in STORE_TZ)."""
    now = _to_store_time(now)
    for offset in range(MAX_LOOKAHEAD_DAYS + 1):
        day = now.date() + timedelta(days=offset)
        hours = _hours(day, holidays)
        if hours is None:
            continue
        opening = datetime.combine(day, hours[0], tzinfo=STORE_TZ)
        if now < opening:
            return opening
        if now.time() < hours[1]:
            return now
    raise NoOpeningFound(now)
