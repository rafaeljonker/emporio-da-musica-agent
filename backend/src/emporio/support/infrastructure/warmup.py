import threading
from collections.abc import Callable
from datetime import UTC, datetime

from emporio.shared.clock import SystemClock
from emporio.support.application.warmup import WarmMode, WarmStage, WarmStatus


class ReadyWarmup:
    """A model that is always ready (provider APIs, fake model)."""

    def __init__(self, mode: WarmMode, reply_p50: Callable[[], float | None]) -> None:
        self._mode = mode
        self._reply_p50 = reply_p50
        self._started_at: datetime | None = None
        self._lock = threading.Lock()

    def start(self) -> WarmStatus:
        with self._lock:
            if self._started_at is None:
                self._started_at = SystemClock().now().astimezone(UTC)
        return self.status()

    def status(self) -> WarmStatus:
        started_at = self._started_at or SystemClock().now().astimezone(UTC)
        return WarmStatus(self._mode, WarmStage.READY, started_at, 0, 0, self._reply_p50())
