from pathlib import Path

import psycopg
import pytest

from emporio.db import connect
from emporio.migrate import apply_migrations

pytestmark = pytest.mark.postgres


def test_apply_migrations_creates_tables_and_is_idempotent(pg_conn: psycopg.Connection):
    pg_conn.execute(
        "DROP TABLE IF EXISTS policy_chunks, product_embeddings, turn_metrics, schema_migrations"
    )
    pg_conn.commit()

    assert apply_migrations(pg_conn) == ["001", "002", "003", "004", "005", "006"]
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


def test_failed_migration_keeps_earlier_ones(pg_conn: psycopg.Connection, tmp_path: Path):
    # Versions 9xx avoid clashing with the real 001-003 rows.
    (tmp_path / "901_ok.sql").write_text("CREATE TABLE tmp_migration_probe (id integer)")
    (tmp_path / "902_bad.sql").write_text("THIS IS NOT SQL")
    try:
        with pytest.raises(psycopg.Error):
            apply_migrations(pg_conn, tmp_path)

        with connect() as other:
            versions = {r[0] for r in other.execute("SELECT version FROM schema_migrations")}
            table = other.execute("SELECT to_regclass('tmp_migration_probe')").fetchone()
        assert "901" in versions
        assert "902" not in versions
        assert table is not None
        assert table[0] is not None
    finally:
        pg_conn.rollback()
        pg_conn.execute("DROP TABLE IF EXISTS tmp_migration_probe")
        pg_conn.execute("DELETE FROM schema_migrations WHERE version IN ('901', '902')")
        pg_conn.commit()


def test_catalog_tables_exist_with_trgm(pg_conn: psycopg.Connection):
    ext = pg_conn.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'").fetchone()
    assert ext is not None
    for table in ("products", "categories", "promotions", "catalog_audit"):
        row = pg_conn.execute("SELECT to_regclass(%s)", (table,)).fetchone()
        assert row is not None
        assert row[0] is not None, table


def _insert_category(conn: psycopg.Connection) -> None:
    conn.execute("INSERT INTO categories (id, name, description) VALUES (1, 'Violões', 'x')")


def test_products_generated_search_columns(pg_conn: psycopg.Connection):
    _insert_category(pg_conn)
    pg_conn.execute(
        "INSERT INTO products (id, name, category_id, description, price, stock, status,"
        " search_doc) VALUES (1, 'Violão Takamine GD-20 NS', 1, 'd', 100, 1, 'active', 'doc')"
    )
    row = pg_conn.execute(
        "SELECT name_key, code_key, tsv @@ plainto_tsquery('portuguese', 'takamine')"
        " FROM products WHERE id = 1"
    ).fetchone()
    assert row == ("violao takamine gd-20 ns", "violaotakaminegd20ns", True)


_INSERT_PRODUCT = (
    "INSERT INTO products (id, name, category_id, description, price, stock, status, source,"
    " owner, search_doc) VALUES (1, 'Violão', 1, 'd', %(price)s, %(stock)s, %(status)s,"
    " %(source)s, NULL, 'doc')"
)


@pytest.mark.parametrize(
    "bad",
    [{"price": 0}, {"stock": -1}, {"status": "sold"}, {"source": "admin"}],  # admin needs an owner
)
def test_products_checks_reject_bad_rows(pg_conn: psycopg.Connection, bad: dict[str, object]):
    _insert_category(pg_conn)
    row: dict[str, object] = {"price": 100, "stock": 1, "status": "active", "source": "seed"}
    with pytest.raises(psycopg.errors.CheckViolation):
        pg_conn.execute(_INSERT_PRODUCT, row | bad)
