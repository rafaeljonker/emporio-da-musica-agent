import psycopg
import pytest

from emporio.migrate import apply_migrations

pytestmark = pytest.mark.postgres


def test_apply_migrations_creates_tables_and_is_idempotent(pg_conn: psycopg.Connection):
    pg_conn.execute("DROP TABLE IF EXISTS policy_chunks, product_embeddings, schema_migrations")
    pg_conn.commit()

    assert apply_migrations(pg_conn) == ["001", "002", "003"]
    assert apply_migrations(pg_conn) == []

    rows = pg_conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    ).fetchall()
    names = {r[0] for r in rows}
    assert {"policy_chunks", "product_embeddings"} <= names


def test_f_unaccent_strips_accents(pg_conn: psycopg.Connection):
    row = pg_conn.execute("SELECT f_unaccent('devolução')").fetchone()
    assert row is not None
    assert row[0] == "devolucao"
