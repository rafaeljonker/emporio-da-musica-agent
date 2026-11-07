import os
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from emporio import ingest
from emporio.platform.db import connect, database_url
from tests.fakes.hash_embedder import HashEmbedder
from tests.pg_guard import pg_skip_reason

pytestmark = pytest.mark.postgres


def test_fresh_database_ingest_seeds_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    reason = pg_skip_reason(os.environ.get("DATABASE_URL"))
    if reason:
        pytest.skip(reason)
    base = urlsplit(database_url())
    name = f"emporio_fresh_{uuid.uuid4().hex[:8]}_test"
    fresh_url = urlunsplit(base._replace(path=f"/{name}"))
    with psycopg.connect(database_url(), autocommit=True) as admin:
        admin.execute(f"CREATE DATABASE {name}")  # pyright: ignore[reportCallIssue, reportArgumentType]
        try:
            monkeypatch.setenv("DATABASE_URL", fresh_url)
            monkeypatch.setattr(ingest, "E5Embedder", HashEmbedder)
            ingest.main()
            with connect(fresh_url) as conn:
                row = conn.execute(
                    "SELECT count(*) FILTER (WHERE embedding IS NOT NULL), count(*),"
                    " to_regclass('product_embeddings') IS NULL FROM products"
                ).fetchone()
        finally:
            admin.execute(f"DROP DATABASE {name} WITH (FORCE)")  # pyright: ignore[reportCallIssue, reportArgumentType]
    assert row == (65, 65, True)
