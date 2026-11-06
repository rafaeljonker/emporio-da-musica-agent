import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException, Request


def require_json(request: Request) -> None:
    media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type != "application/json":
        raise HTTPException(status_code=415, detail="json_required")


class SlidingWindow:
    """Allow at most `limit` hits per `seconds` for each key.

    ponytail: in memory per process; behind several containers the limit multiplies, move it
    to a shared store (one Postgres row per key) if that matters. Behind a proxy all clients may
    share one IP, so the per-IP limit can then act as a global one.
    Every call sweeps all keys, so an idle key is dropped; O(keys), fine for a demo.
    """

    def __init__(self, limit: int, seconds: float) -> None:
        self._limit = limit
        self._seconds = seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            for name in list(self._hits):
                stale = self._hits[name]
                while stale and now - stale[0] >= self._seconds:
                    stale.popleft()
                if not stale:
                    del self._hits[name]
            hits = self._hits.setdefault(key, deque())
            if len(hits) >= self._limit:
                return False
            hits.append(now)
            return True


class ThreadLocks:
    """One turn at a time per thread; a lock older than `stale_after` seconds is reclaimed.

    ponytail: in-process lock, pg_try_advisory_lock if the API runs >1 container
    """

    def __init__(
        self, stale_after: float = 300.0, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._stale_after = stale_after
        self._clock = clock
        self._held: dict[str, float] = {}
        self._lock = threading.Lock()

    def try_acquire(self, thread_id: str) -> float | None:
        """Return the owner token (the acquire time), or None if the thread is busy."""
        now = self._clock()
        with self._lock:
            since = self._held.get(thread_id)
            if since is not None and now - since < self._stale_after:
                return None
            self._held[thread_id] = now
            return now

    def release(self, thread_id: str, token: float) -> None:
        """Free the lock only if `token` still owns it (a reclaimed owner must not free it)."""
        with self._lock:
            if self._held.get(thread_id) == token:
                del self._held[thread_id]


@dataclass(frozen=True)
class Session:
    sid: str
    customer_id: int | None


def require_session(request: Request) -> Session:
    sid = request.session.get("sid")
    if not isinstance(sid, str) or not sid:
        raise HTTPException(status_code=401, detail="unauthenticated")
    customer_id = request.session.get("customer_id")
    return Session(sid, customer_id if isinstance(customer_id, int) else None)
