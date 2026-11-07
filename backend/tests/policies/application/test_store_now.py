from datetime import date, datetime, time

from emporio.policies.application.store_now import StoreNow
from emporio.shared.clock import STORE_TZ, FixedClock


def test_store_now_uses_clock() -> None:
    clock = FixedClock(date(2026, 2, 22), time(10, 0))
    status = StoreNow(clock, frozenset())()
    assert status.open is False
    assert status.now == clock.now()
    assert status.next_opening == datetime(2026, 2, 23, 9, 0, tzinfo=STORE_TZ)
