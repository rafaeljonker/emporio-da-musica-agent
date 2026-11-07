import hmac
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Request

from emporio.api.errors import ApiErrorCode, http_error
from emporio.config import Settings


def require_json(request: Request) -> None:
    media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type != "application/json":
        raise http_error(ApiErrorCode.JSON_REQUIRED)


def client_ip(request: Request, settings: Settings) -> str:
    """The caller's IP: the proxy's X-Client-IP only when X-Proxy-Auth matches proxy_secret.

    The raw *.modal.run URL is public, so X-Client-IP or X-Forwarded-For alone could be forged.
    """
    secret = settings.proxy_secret.get_secret_value() if settings.proxy_secret else ""
    given = request.headers.get("x-proxy-auth", "")
    trusted = request.headers.get("x-client-ip", "").strip()
    if secret and trusted and hmac.compare_digest(given.encode(), secret.encode()):
        return trusted
    return request.client.host if request.client else "unknown"


class SlidingWindow:
    """Allow at most `limit` hits per `seconds` for each key.

    ponytail: in memory per process; behind several containers the limit multiplies, move it
    to a shared store (one Postgres row per key) if that matters. Behind a proxy all clients may
    share one IP unless client_ip trusts the proxy's header.
    Every call sweeps all keys, so an idle key is dropped; O(keys), fine for a demo.
    """

    def __init__(self, limit: int, seconds: float) -> None:
        self._limit = limit
        self._seconds = seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def full(self, key: str) -> bool:
        """True when `key` is at its limit right now; records nothing."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits.get(key, deque())
            return sum(1 for t in hits if now - t < self._seconds) >= self._limit

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
        raise http_error(ApiErrorCode.UNAUTHENTICATED)
    customer_id = request.session.get("customer_id")
    return Session(sid, customer_id if isinstance(customer_id, int) else None)
