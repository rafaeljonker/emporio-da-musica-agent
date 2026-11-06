from concurrent.futures import ThreadPoolExecutor

import pytest
from psycopg_pool import ConnectionPool

from emporio.catalog.infrastructure.csv_catalog_repository import CsvCatalogRepository
from emporio.catalog.infrastructure.pg_product_index import PgProductIndex
from emporio.db import IndexUnavailable, make_pool
from emporio.policies.infrastructure.pdf_sections import read_policy_chunks
from emporio.policies.infrastructure.pg_policy_index import PgPolicyIndex
from tests.fakes.hash_embedder import HashEmbedder

pytestmark = pytest.mark.postgres

UNREACHABLE = "postgresql://emporio:x@127.0.0.1:1/emporio_test"


def test_concurrent_searches_share_pool(pg_pool: ConnectionPool) -> None:
    embedder = HashEmbedder()
    policies = PgPolicyIndex(pg_pool, embedder)
    products = PgProductIndex(pg_pool, embedder)
    policies.replace_all(read_policy_chunks())
    repo = CsvCatalogRepository()
    products.replace_all(repo.products(), {c.id: c.name for c in repo.categories()})

    def work(i: int) -> tuple[int, int]:
        return len(policies.search("prazo de troca", 5)), len(products.similar("violao", 5))

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(work, range(8)))

    assert results == [(5, 5)] * 8


def test_unreachable_db_raises_index_unavailable() -> None:
    pool = make_pool(UNREACHABLE)
    pool.timeout = 1
    try:
        with pytest.raises(IndexUnavailable):
            PgPolicyIndex(pool, HashEmbedder()).search("troca", 3)
        with pytest.raises(IndexUnavailable):
            PgProductIndex(pool, HashEmbedder()).similar("violao", 3)
    finally:
        pool.close()
