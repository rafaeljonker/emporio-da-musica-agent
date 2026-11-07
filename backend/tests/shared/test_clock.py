from datetime import date, datetime, time, timedelta

from emporio.platform.clock import SystemClock
from emporio.shared.clock import STORE_TZ, FixedClock


def test_fixed_clock_returns_fixed_date() -> None:
    assert FixedClock(date(2026, 2, 20)).today() == date(2026, 2, 20)


def test_system_clock_uses_store_timezone() -> None:
    assert isinstance(SystemClock().today(), date)


def test_fixed_clock_now_is_aware_noon_in_store_tz() -> None:
    assert FixedClock(date(2026, 2, 20)).now() == datetime(2026, 2, 20, 12, 0, tzinfo=STORE_TZ)


def test_fixed_clock_now_uses_given_time() -> None:
    now = FixedClock(date(2026, 2, 20), at=time(9, 30)).now()
    assert now == datetime(2026, 2, 20, 9, 30, tzinfo=STORE_TZ)


def test_system_clock_now_is_aware() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(hours=-4)
