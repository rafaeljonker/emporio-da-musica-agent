import os
from collections.abc import Iterator

import psycopg
import pytest
from psycopg_pool import ConnectionPool

from emporio.catalog.infrastructure.csv_catalog_repository import CsvCatalogRepository
from emporio.catalog.infrastructure.pg_catalog_repository import PgCatalogRepository
from emporio.catalog.infrastructure.pg_catalog_writer import PgCatalogWriter
from emporio.db import connect, make_pool
from emporio.migrate import apply_migrations
from tests.fakes.hash_embedder import HashEmbedder
from tests.pg_guard import pg_skip_reason


@pytest.fixture
def pg_conn() -> Iterator[psycopg.Connection]:
    reason = pg_skip_reason(os.environ.get("DATABASE_URL"))
    if reason:
        pytest.skip(reason)
    conn = connect()
    apply_migrations(conn)
    yield conn
    conn.rollback()
    conn.execute(
        "TRUNCATE policy_chunks, product_embeddings, promotions, products, categories,"
        " catalog_audit RESTART IDENTITY CASCADE"
    )
    # Not owned by a column, so RESTART IDENTITY leaves it alone.
    conn.execute("ALTER SEQUENCE products_admin_id_seq RESTART")
    conn.commit()
    conn.close()


@pytest.fixture
def pg_pool(pg_conn: psycopg.Connection) -> Iterator[ConnectionPool]:
    """Pool over the guarded `_test` database; `pg_conn` already migrated and cleans up."""
    pool = make_pool()
    yield pool
    pool.close()


@pytest.fixture
def catalog_repo(pg_pool: ConnectionPool) -> PgCatalogRepository:
    csv = CsvCatalogRepository()
    PgCatalogWriter(pg_pool, HashEmbedder()).seed(
        csv.categories(), csv.products(), csv.promotions()
    )
    return PgCatalogRepository(pg_pool, HashEmbedder())
