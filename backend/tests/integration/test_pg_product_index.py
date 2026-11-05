import psycopg
import pytest

from emporio.catalog.infrastructure.csv_catalog_repository import CsvCatalogRepository
from emporio.catalog.infrastructure.pg_product_index import PgProductIndex
from tests.fakes.hash_embedder import HashEmbedder

pytestmark = pytest.mark.postgres


def _fill(conn: psycopg.Connection) -> PgProductIndex:
    repo = CsvCatalogRepository()
    index = PgProductIndex(conn, HashEmbedder())
    index.replace_all(repo.products(), {c.id: c.name for c in repo.categories()})
    return index


def _count(conn: psycopg.Connection) -> int:
    row = conn.execute("SELECT count(*) FROM product_embeddings").fetchone()
    assert row is not None
    return row[0]


def test_product_index_replace_all_is_idempotent(pg_conn: psycopg.Connection) -> None:
    _fill(pg_conn)
    _fill(pg_conn)

    assert _count(pg_conn) == 65


def test_similar_returns_k_distinct_product_ids(pg_conn: psycopg.Connection) -> None:
    ids = _fill(pg_conn).similar("violao para iniciante", 10)

    assert len(ids) == len(set(ids)) == 10
