from datetime import date, datetime

from emporio.shared.clock import STORE_TZ


class SystemClock:
    """The wall clock in the store's timezone; the `Clock` port's production adapter."""

    def today(self) -> date:
        return self.now().date()

    def now(self) -> datetime:
        return datetime.now(STORE_TZ)
