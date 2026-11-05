import os
from collections.abc import Iterator

import psycopg
import pytest

from emporio.db import connect
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
    conn.execute("TRUNCATE policy_chunks, product_embeddings")
    conn.commit()
    conn.close()
