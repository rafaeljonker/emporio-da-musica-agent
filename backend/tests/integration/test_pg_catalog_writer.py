import logging
from collections.abc import Sequence

import psycopg
import pytest
from psycopg_pool import ConnectionPool

from emporio.catalog.application.ports import CatalogFilter
from emporio.catalog.domain.product import ProductDraft, ProductStatus
from emporio.catalog.infrastructure.pg_catalog_repository import PgCatalogRepository
from emporio.catalog.infrastructure.pg_catalog_writer import PgCatalogWriter
from emporio.shared.money import Money
from tests.fakes.hash_embedder import HashEmbedder

pytestmark = pytest.mark.postgres

ROZINI = ProductDraft(
    "Cavaquinho Rozini Choro Profissional RC-77X",
    5,
    "Cavaquinho de choro com tampo maciço",
    Money.from_str("1234.50"),
    4,
    ProductStatus.ACTIVE,
    (("cordas", "aço"),),
)


class FailingEmbedder(HashEmbedder):
    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        raise RuntimeError


class CountingEmbedder(HashEmbedder):
    def __init__(self) -> None:
        self.passages = 0

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        self.passages += len(texts)
        return super().embed_passages(texts)


def _row(conn: psycopg.Connection, product_id: int) -> tuple[object, ...]:
    row = conn.execute(
        "SELECT name, price, stock, embedding IS NULL, embedded_hash, updated_at"
        " FROM products WHERE id = %s",
        (product_id,),
    ).fetchone()
    assert row is not None
    return row


def test_created_product_is_found_by_next_search(
    catalog_repo: PgCatalogRepository, pg_pool: ConnectionPool, pg_conn: psycopg.Connection
) -> None:
    created = PgCatalogWriter(pg_pool, HashEmbedder()).create("a", ROZINI)

    top = catalog_repo.search("cavaquinho rozini", CatalogFilter(available_only=True), 10)
    assert created.id >= 100000
    assert created.id in [p.id for p in top[:3]]
    audit = pg_conn.execute(
        "SELECT actor, action, product_id, after->>'price' FROM catalog_audit"
    ).fetchall()
    assert audit == [("a", "create", created.id, "1234.50")]


def test_create_with_failing_embedder_saves_and_is_searchable(
    catalog_repo: PgCatalogRepository,
    pg_pool: ConnectionPool,
    pg_conn: psycopg.Connection,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        created = PgCatalogWriter(pg_pool, FailingEmbedder()).create("a", ROZINI)

    assert _row(pg_conn, created.id)[3] is True  # embedding IS NULL
    assert "product embed failed: RuntimeError" in caplog.text
    # The type only: a traceback could carry the product text into the logs.
    assert all(r.exc_info is None for r in caplog.records if r.levelno >= logging.WARNING)
    found = catalog_repo.search("rozini", CatalogFilter(available_only=True), 10)
    assert created.id in [p.id for p in found]


def test_update_ignores_seed_and_foreign_rows(
    catalog_repo: PgCatalogRepository, pg_pool: ConnectionPool, pg_conn: psycopg.Connection
) -> None:
    writer = PgCatalogWriter(pg_pool, HashEmbedder())
    mine = writer.create("a", ROZINI)
    seed_before, mine_before = _row(pg_conn, 95), _row(pg_conn, mine.id)

    assert writer.update("a", 95, ROZINI) is None
    assert writer.update("b", mine.id, ROZINI) is None

    assert (_row(pg_conn, 95), _row(pg_conn, mine.id)) == (seed_before, mine_before)


def test_update_own_row_changes_it_and_audits(
    catalog_repo: PgCatalogRepository, pg_pool: ConnectionPool, pg_conn: psycopg.Connection
) -> None:
    writer = PgCatalogWriter(pg_pool, HashEmbedder())
    mine = writer.create("a", ROZINI)
    changed = ProductDraft(
        "Cavaquinho Rozini Studio",
        ROZINI.category_id,
        ROZINI.description,
        Money.from_str("999"),
        2,
        ROZINI.status,
        (),
    )

    updated = writer.update("a", mine.id, changed)

    assert updated == changed.with_id(mine.id)
    assert catalog_repo.get(mine.id) == updated
    assert [p.id for p in writer.own("a")] == [mine.id]
    assert writer.own("b") == []
    assert writer.admin_total() == 1
    actions = pg_conn.execute("SELECT action FROM catalog_audit ORDER BY id").fetchall()
    assert actions == [("create",), ("update",)]


def test_price_only_update_keeps_embedding(
    catalog_repo: PgCatalogRepository, pg_pool: ConnectionPool, pg_conn: psycopg.Connection
) -> None:
    embedder = CountingEmbedder()
    writer = PgCatalogWriter(pg_pool, embedder)
    mine = writer.create("a", ROZINI)
    hash_before = _row(pg_conn, mine.id)[4]
    embedder.passages = 0

    cheaper = ProductDraft(
        ROZINI.name,
        ROZINI.category_id,
        ROZINI.description,
        Money.from_str("1000"),
        9,
        ROZINI.status,
        ROZINI.specs,
    )
    writer.update("a", mine.id, cheaper)

    assert embedder.passages == 0
    _, price, stock, no_vector, hash_after, _ = _row(pg_conn, mine.id)
    assert (price, stock, no_vector) == (Money.from_str("1000").amount, 9, False)
    assert hash_after == hash_before
