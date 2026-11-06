import logging
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime

import httpx

from emporio.shared.clock import SystemClock
from emporio.support.application.warmup import WarmMode, WarmStage, WarmStatus


class ReadyWarmup:
    """A model that is always ready (provider APIs, fake model)."""

    def __init__(self, mode: WarmMode, reply_p50: Callable[[], float | None]) -> None:
        self.mode = mode
        self.expected_seconds = 0
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
        return WarmStatus(self.mode, WarmStage.READY, started_at, 0, 0, _safe_p50(self._reply_p50))


def _utc_now() -> datetime:
    return SystemClock().now().astimezone(UTC)


def _safe_p50(reply_p50: Callable[[], float | None]) -> float | None:
    """The p50 is decoration: a failing metrics query must never break the warm status."""
    try:
        return reply_p50()
    except Exception:
        logging.getLogger(__name__).warning("reply p50 unavailable", exc_info=True)
        return None


def vllm_health_probe(
    base_url: str, api_key: str, timeout: float = 10, transport: httpx.BaseTransport | None = None
) -> Callable[[], bool]:
    """True only when vLLM `/health` answers 200; a 303 (Modal cold start) or a timeout is False."""
    url = base_url.rstrip("/").removesuffix("/v1") + "/health"

    def probe() -> bool:
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            with httpx.Client(
                timeout=timeout, follow_redirects=False, transport=transport
            ) as client:
                return client.get(url, headers=headers).status_code == 200
        except httpx.HTTPError:
            return False

    return probe


class ProbeWarmup:
    """Polls `probe` in one daemon thread until it is true or the deadline passes.

    ponytail: warm state lives in this process; behind several containers each one probes on its
    own. Upgrade: a one-row warm table every container reads.
    """

    def __init__(
        self,
        probe: Callable[[], bool],
        mode: WarmMode,
        expected_seconds: int,
        reply_p50: Callable[[], float | None],
        *,
        stage: WarmStage = WarmStage.SERVER_STARTING,
        deadline_seconds: float = 600,
        interval_seconds: float = 2,
        ready_ttl_seconds: float = 300,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.mode = mode
        self.expected_seconds = expected_seconds
        self._probe = probe
        self._reply_p50 = reply_p50
        self._waiting_stage = stage
        self._deadline = deadline_seconds
        self._interval = interval_seconds
        self._ready_ttl = ready_ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._started_at: datetime | None = None
        self._ended_at: datetime | None = None
        self._stage = stage
        self._thread: threading.Thread | None = None

    def start(self) -> WarmStatus:
        with self._lock:
            now = self._clock()
            # A READY older than the TTL may be a GPU that scaled down since: probe again.
            stale = (
                self._stage is WarmStage.READY
                and self._ended_at is not None
                and (now - self._ended_at).total_seconds() > self._ready_ttl
            )
            if self._started_at is None or stale:
                self._started_at = now
            if self._thread is None or self._stage is WarmStage.FAILED or stale:
                self._stage = self._waiting_stage
                self._ended_at = None
                self._thread = threading.Thread(target=self._run, args=(now,), daemon=True)
                self._thread.start()
        return self.status()

    def join(self, timeout: float) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def status(self) -> WarmStatus:
        if self._thread is None:
            self.start()
        with self._lock:
            now = self._clock()
            started_at = self._started_at or now
            elapsed = (self._ended_at or now) - started_at
            stage = self._stage
        return WarmStatus(
            self.mode,
            stage,
            started_at,
            int(elapsed.total_seconds()),
            self.expected_seconds,
            _safe_p50(self._reply_p50),
        )

    def _is_up(self) -> bool:
        try:
            return self._probe()
        except Exception:
            logging.getLogger(__name__).debug("warm probe raised", exc_info=True)
            return False

    def _run(self, run_started: datetime) -> None:
        while True:
            up = self._is_up()
            now = self._clock()
            expired = (now - run_started).total_seconds() >= self._deadline
            if up or expired:
                with self._lock:
                    self._stage = WarmStage.READY if up else WarmStage.FAILED
                    self._ended_at = now
                return
            time.sleep(self._interval)
