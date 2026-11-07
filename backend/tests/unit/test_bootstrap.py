from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace

import pytest

from emporio import bootstrap
from emporio.catalog.infrastructure.pg_catalog_repository import PgCatalogRepository
from emporio.config import LangfuseUnreachable, Provider, Settings
from emporio.orders.infrastructure.csv_order_repository import CsvCustomerRepository


class FakePool:
    closed = False

    def __enter__(self) -> "FakePool":
        return self

    def __exit__(self, *exc: object) -> None:
        self.closed = True


@contextmanager
def _conn() -> Iterator[object]:
    yield object()


def test_toolbox_pool_opens_at_the_settings_size(monkeypatch: pytest.MonkeyPatch) -> None:
    sizes: list[object] = []

    def make_pool(url: str, **kwargs: object) -> FakePool:
        sizes.append((kwargs.get("min_size"), kwargs.get("max_size")))
        return FakePool()

    monkeypatch.setattr(bootstrap, "make_pool", make_pool)
    monkeypatch.setattr(bootstrap, "E5Embedder", lambda: object())
    with ExitStack() as stack:
        bootstrap.build_toolbox(stack, "postgresql://unused", Settings(db_pool_max=20))
    assert sizes == [(20, 20)]  # opened at full size, not grown under load


def test_toolbox_serves_the_postgres_catalog_and_shares_the_embedder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    embedder = object()
    monkeypatch.setattr(bootstrap, "make_pool", lambda url, **_: FakePool())
    monkeypatch.setattr(bootstrap, "E5Embedder", lambda: embedder)
    with ExitStack() as stack:
        box, _, _, shared = bootstrap.build_toolbox(stack, "postgresql://unused", Settings())
    assert isinstance(box.catalog, PgCatalogRepository)
    assert shared is embedder  # the writer reuses it, so e5 loads once


def test_failed_langfuse_check_closes_what_was_opened(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = FakePool()
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    patches = {
        "connect": lambda url: _conn(),
        "apply_migrations": lambda conn: [],
        "setup_checkpointer": lambda url: None,
        "make_pool": lambda url, **_: pool,
        "E5Embedder": lambda: object(),
        "PgPolicyIndex": lambda pool, embedder: object(),
        "make_chat_model": lambda settings: object(),
        "make_guard_model": lambda settings: object(),
        "make_checkpointer": lambda url, **_: SimpleNamespace(conn=FakePool()),
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
    seen_names: list[object] = []
    saver_sizes: list[object] = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    patches = {
        "connect": lambda url: _conn(),
        "apply_migrations": lambda conn: [],
        "setup_checkpointer": lambda url: None,
        "make_pool": lambda url, **_: FakePool(),
        "E5Embedder": lambda: object(),
        "PgPolicyIndex": lambda pool, embedder: object(),
        "make_chat_model": lambda settings: pytest.fail("fake mode needs no provider model"),
        "make_classifier": lambda model: pytest.fail("fake mode needs no classifier call"),
        "make_checkpointer": lambda url, **kw: (
            saver_sizes.append(kw.get("max_size")) or SimpleNamespace(conn=FakePool())
        ),
        "build_tools": lambda box: [],
        "build_graph": lambda *args: built.append(args),
        "make_langfuse": lambda settings, names: seen_names.append(names),
        "LangfuseTracerFactory": lambda *args: object(),
    }
    for name, fake in patches.items():
        monkeypatch.setattr(bootstrap, name, fake)
    agent = bootstrap.build_agent(Settings(fake_model=True, db_pool_max=20))
    agent.close()
    assert saver_sizes == [20]  # the checkpointer pool follows DB_POOL_MAX too
    model, _, classify, _ = built[0]
    assert isinstance(model, ScriptedChatModel)
    assert seen_names == [CsvCustomerRepository().names()]
    assert callable(classify)
    assert classify([HumanMessage("vai se ferrar")]) is Scope.LOJA


def test_build_agent_wires_catalog_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    from emporio.catalog.application.admin import CatalogAdminService
    from emporio.catalog.infrastructure.pg_catalog_writer import PgCatalogWriter

    embedder = object()
    writers: list[tuple[object, object]] = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    patches = {
        "connect": lambda url: _conn(),
        "apply_migrations": lambda conn: [],
        "setup_checkpointer": lambda url: None,
        "make_pool": lambda url, **_: FakePool(),
        "E5Embedder": lambda: embedder,
        "PgPolicyIndex": lambda pool, embedder: object(),
        "make_checkpointer": lambda url, **_: SimpleNamespace(conn=FakePool()),
        "build_tools": lambda box: [],
        "build_graph": lambda *args: object(),
        "make_langfuse": lambda settings, names: None,
        "LangfuseTracerFactory": lambda *args: object(),
        "PgCatalogWriter": lambda pool, emb: (
            writers.append((pool, emb)) or PgCatalogWriter(pool, emb)
        ),
    }
    for name, fake in patches.items():
        monkeypatch.setattr(bootstrap, name, fake)
    agent = bootstrap.build_agent(Settings(fake_model=True))
    agent.close()
    assert isinstance(agent.catalog_admin, CatalogAdminService)
    assert [emb for _, emb in writers] == [embedder]  # the toolbox's embedder, loaded once
