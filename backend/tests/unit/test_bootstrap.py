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

    def unreachable(settings: Settings, names: object) -> None:
        raise LangfuseUnreachable("http://unused")

    monkeypatch.setattr(bootstrap, "make_langfuse", unreachable)
    with pytest.raises(LangfuseUnreachable):
        bootstrap.build_agent(Settings(provider=Provider.GEMMA))
    assert pool.closed


def test_fake_model_wires_scripted_model_and_store_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    from langchain_core.messages import HumanMessage

    from emporio.support.domain.scope import Scope
    from emporio.support.infrastructure.llm.scripted import ScriptedChatModel

    built: list[tuple[object, ...]] = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    patches = {
        "connect": lambda url: _conn(),
        "apply_migrations": lambda conn: [],
        "setup_checkpointer": lambda url: None,
        "make_pool": lambda url: FakePool(),
        "E5Embedder": lambda: object(),
        "PgProductIndex": lambda pool, embedder: object(),
        "PgPolicyIndex": lambda pool, embedder: object(),
        "make_chat_model": lambda settings: pytest.fail("fake mode needs no provider model"),
        "make_classifier": lambda model: pytest.fail("fake mode needs no classifier call"),
        "make_checkpointer": lambda url: SimpleNamespace(conn=FakePool()),
        "build_tools": lambda box: [],
        "build_graph": lambda *args: built.append(args),
        "make_langfuse": lambda settings, names: object(),
        "LangfuseTracerFactory": lambda *args: object(),
    }
    for name, fake in patches.items():
        monkeypatch.setattr(bootstrap, name, fake)
    agent = bootstrap.build_agent(Settings(fake_model=True))
    agent.close()
    model, _, classify, _ = built[0]
    assert isinstance(model, ScriptedChatModel)
    assert callable(classify)
    assert classify([HumanMessage("vai se ferrar")]) is Scope.LOJA
