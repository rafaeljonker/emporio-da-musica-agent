import threading

import pytest

from emporio.support.infrastructure import checkpointer


class FakePool:
    def __init__(self, url: str, **kwargs: object) -> None:
        self.opened_with = kwargs


def test_pool_is_opened_at_the_callers_size(monkeypatch: pytest.MonkeyPatch) -> None:
    # Growing one connection at a time over a high-RTT proxy queued turns for seconds.
    monkeypatch.setattr(checkpointer, "ConnectionPool", FakePool)
    saver = checkpointer.make_checkpointer("postgresql://unused", max_size=20)
    pool = saver.conn
    assert isinstance(pool, FakePool)
    assert (pool.opened_with["min_size"], pool.opened_with["max_size"]) == (20, 20)


def test_checkpoint_io_is_not_serialized_across_threads(monkeypatch: pytest.MonkeyPatch) -> None:
    # Each call checks out its own pooled connection: one saver-wide lock would queue every turn.
    monkeypatch.setattr(checkpointer, "ConnectionPool", FakePool)
    saver = checkpointer.make_checkpointer("postgresql://unused")
    entered = threading.Event()

    def other_turn() -> None:
        with saver.lock:
            entered.set()

    with saver.lock:
        worker = threading.Thread(target=other_turn)
        worker.start()
        assert entered.wait(1)
    worker.join()
