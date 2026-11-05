import os
from collections.abc import Iterator

import psycopg
import pytest

from emporio.db import connect
from emporio.migrate import apply_migrations


@pytest.fixture
def pg_conn() -> Iterator[psycopg.Connection]:
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set; run `make test-pg`")
    conn = connect()
    apply_migrations(conn)
    yield conn
    conn.rollback()
    conn.execute("TRUNCATE policy_chunks, product_embeddings")
    conn.commit()
    conn.close()
