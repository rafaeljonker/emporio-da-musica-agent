from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from emporio import bootstrap
from emporio.config import LangfuseUnreachable, Provider, Settings


class FakePool:
    closed = False

    def __enter__(self) -> "FakePool":
        return self

    def __exit__(self, *exc: object) -> None:
        self.closed = True


@contextmanager
def _conn() -> Iterator[object]:
    yield object()


def test_failed_langfuse_check_closes_what_was_opened(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = FakePool()
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    patches = {
        "connect": lambda url: _conn(),
        "apply_migrations": lambda conn: [],
        "setup_checkpointer": lambda url: None,
        "make_pool": lambda url: pool,
        "E5Embedder": lambda: object(),
        "PgProductIndex": lambda pool, embedder: object(),
        "PgPolicyIndex": lambda pool, embedder: object(),
        "make_chat_model": lambda settings: object(),
        "make_checkpointer": lambda url: SimpleNamespace(conn=FakePool()),
        "build_tools": lambda box: [],
        "make_classifier": lambda model: object(),
        "build_graph": lambda *args: object(),
    }
    for name, fake in patches.items():
        monkeypatch.setattr(bootstrap, name, fake)

    def unreachable(settings: Settings) -> None:
        raise LangfuseUnreachable("http://unused")

    monkeypatch.setattr(bootstrap, "make_langfuse", unreachable)
    with pytest.raises(LangfuseUnreachable):
        bootstrap.build_agent(Settings(provider=Provider.GEMMA))
    assert pool.closed
