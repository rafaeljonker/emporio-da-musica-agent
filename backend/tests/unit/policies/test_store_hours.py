from datetime import UTC, date, datetime, time, timedelta

import pytest

from emporio.policies.domain.store_hours import (
    NaiveDatetimeError,
    NoOpeningFound,
    is_open,
    next_opening,
)
from emporio.policies.infrastructure.holidays import STORE_HOLIDAYS
from emporio.shared.clock import STORE_TZ
from emporio.shared.errors import DomainError

HOLIDAYS = frozenset({date(2026, 4, 21)})


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=STORE_TZ)


@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    [(8, 59, False), (9, 0, True), (17, 59, True), (18, 0, False)],
)
def test_open_boundaries(hour: int, minute: int, expected: bool) -> None:
    assert is_open(at(date(2026, 2, 20), hour, minute), HOLIDAYS) is expected


def test_saturday_closes_at_13() -> None:
    assert is_open(at(date(2026, 2, 21), 12, 59), HOLIDAYS)
    assert not is_open(at(date(2026, 2, 21), 13), HOLIDAYS)


def test_sunday_closed() -> None:
    assert not is_open(at(date(2026, 2, 22), 10), HOLIDAYS)


def test_holiday_closed() -> None:
    assert not is_open(at(date(2026, 4, 21), 10), HOLIDAYS)


def test_next_opening_from_saturday_afternoon_is_monday_9() -> None:
    assert next_opening(at(date(2026, 2, 21), 13), HOLIDAYS) == at(date(2026, 2, 23), 9)


def test_next_opening_skips_sunday_and_holiday() -> None:
    holidays = frozenset({date(2026, 4, 20)})
    assert next_opening(at(date(2026, 4, 18), 15), holidays) == at(date(2026, 4, 21), 9)


def test_next_opening_before_opening_same_day() -> None:
    assert next_opening(at(date(2026, 2, 20), 7), HOLIDAYS) == at(date(2026, 2, 20), 9)


def test_next_opening_when_open_is_now() -> None:
    now = at(date(2026, 2, 20), 10)
    assert next_opening(now, HOLIDAYS) == now


def test_holiday_set_is_within_2025_2026_and_has_key_dates() -> None:
    assert {d.year for d in STORE_HOLIDAYS} == {2025, 2026}
    assert date(2026, 12, 25) in STORE_HOLIDAYS
    assert date(2026, 4, 3) in STORE_HOLIDAYS
    assert date(2025, 4, 18) in STORE_HOLIDAYS


def test_utc_input_is_converted_to_store_time() -> None:
    utc_now = datetime(2026, 2, 20, 21, 0, tzinfo=UTC)  # 17:00 in Campo Grande
    assert is_open(utc_now, HOLIDAYS)
    result = next_opening(utc_now, HOLIDAYS)
    assert result == utc_now
    assert result.utcoffset() == utc_now.astimezone(STORE_TZ).utcoffset()


def test_store_hours_naive_datetime_raises_plain_exception_not_domain_error() -> None:
    naive = datetime(2026, 2, 20, 10, 0)  # noqa: DTZ001
    with pytest.raises(NaiveDatetimeError) as closed:
        is_open(naive, HOLIDAYS)
    with pytest.raises(NaiveDatetimeError):
        next_opening(naive, HOLIDAYS)
    assert not isinstance(closed.value, DomainError)  # a bug, not an expected failure


def test_no_opening_within_14_days_raises() -> None:
    start = date(2026, 3, 2)
    holidays = frozenset(start + timedelta(days=i) for i in range(16))
    with pytest.raises(NoOpeningFound) as err:
        next_opening(at(start, 10), holidays)
    assert not isinstance(err.value, DomainError)
