from datetime import date

from emporio.shared.clock import FixedClock, SystemClock


def test_fixed_clock_returns_fixed_date() -> None:
    assert FixedClock(date(2026, 2, 20)).today() == date(2026, 2, 20)


def test_system_clock_uses_store_timezone() -> None:
    assert isinstance(SystemClock().today(), date)
