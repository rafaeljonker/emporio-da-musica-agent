import os
from collections.abc import Iterator

import psycopg
import pytest
from psycopg_pool import ConnectionPool

from emporio.db import connect, make_pool
from emporio.migrate import apply_migrations
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
    conn.commit()
    conn.close()


@pytest.fixture
def pg_pool(pg_conn: psycopg.Connection) -> Iterator[ConnectionPool]:
    """Pool over the guarded `_test` database; `pg_conn` already migrated and cleans up."""
    pool = make_pool()
    yield pool
    pool.close()
