import os
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
from pgvector import Vector

from emporio.db import connect, database_url
from emporio.migrate import apply_migrations
from tests.pg_guard import pg_skip_reason

pytestmark = pytest.mark.postgres


def test_fresh_database_migrate_then_insert_vector() -> None:
    reason = pg_skip_reason(os.environ.get("DATABASE_URL"))
    if reason:
        pytest.skip(reason)
    base = urlsplit(database_url())
    name = f"emporio_fresh_{uuid.uuid4().hex[:8]}"
    fresh_url = urlunsplit(base._replace(path=f"/{name}"))
    with psycopg.connect(database_url(), autocommit=True) as admin:
        admin.execute(f"CREATE DATABASE {name}")  # pyright: ignore[reportCallIssue, reportArgumentType]
        try:
            with connect(fresh_url) as conn:
                apply_migrations(conn)
                conn.execute(
                    "INSERT INTO product_embeddings (product_id, embedding) VALUES (1, %s)",
                    (Vector([0.0] * 383 + [1.0]),),
                )
        finally:
            admin.execute(f"DROP DATABASE {name} WITH (FORCE)")  # pyright: ignore[reportCallIssue, reportArgumentType]
