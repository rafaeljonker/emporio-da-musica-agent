import threading
import time
from collections import deque
from dataclasses import dataclass

from fastapi import HTTPException, Request


def require_json(request: Request) -> None:
    media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type != "application/json":
        raise HTTPException(status_code=415, detail="json_required")


class SlidingWindow:
    """Allow at most `limit` hits per `seconds` for each key.

    ponytail: in memory per process; behind several containers the limit multiplies, move it
    to a shared store (one Postgres row per key) if that matters.
    """

    def __init__(self, limit: int, seconds: float) -> None:
        self._limit = limit
        self._seconds = seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self._seconds:
                hits.popleft()
            if len(hits) >= self._limit:
                return False
            hits.append(now)
            return True


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
