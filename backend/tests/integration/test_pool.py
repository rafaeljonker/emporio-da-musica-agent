from concurrent.futures import ThreadPoolExecutor

import pytest
from psycopg_pool import ConnectionPool

from emporio.catalog.application.ports import CatalogFilter
from emporio.catalog.infrastructure.pg_catalog_repository import PgCatalogRepository
from emporio.db import IndexUnavailable, make_pool
from emporio.policies.infrastructure.pdf_sections import read_policy_chunks
from emporio.policies.infrastructure.pg_policy_index import PgPolicyIndex
from tests.fakes.hash_embedder import HashEmbedder

pytestmark = pytest.mark.postgres

UNREACHABLE = "postgresql://emporio:x@127.0.0.1:1/emporio_test"


def test_concurrent_searches_share_pool(
    pg_pool: ConnectionPool, catalog_repo: PgCatalogRepository
) -> None:
    policies = PgPolicyIndex(pg_pool, HashEmbedder())
    policies.replace_all(read_policy_chunks())

    def work(i: int) -> tuple[int, int]:
        products = catalog_repo.search("violao", CatalogFilter(), 5)
        return len(policies.search("prazo de troca", 5)), len(products)

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(work, range(8)))

    assert results == [(5, 5)] * 8


def test_unreachable_db_raises_index_unavailable() -> None:
    pool = make_pool(UNREACHABLE, timeout=1)
    try:
        with pytest.raises(IndexUnavailable):
            PgPolicyIndex(pool, HashEmbedder()).search("troca", 3)
        with pytest.raises(IndexUnavailable):
            PgCatalogRepository(pool, HashEmbedder()).search("violao", CatalogFilter(), 3)
    finally:
        pool.close()


def test_unreachable_db_fails_catalog_writes_as_unavailable() -> None:
    from emporio.catalog.domain.product import ProductDraft, ProductStatus
    from emporio.catalog.infrastructure.pg_catalog_writer import PgCatalogWriter
    from emporio.shared.money import Money

    draft = ProductDraft("Violão", 5, "", Money.from_str("10"), 1, ProductStatus.ACTIVE, ())
    pool = make_pool(UNREACHABLE, timeout=1)
    writer = PgCatalogWriter(pool, HashEmbedder())
    try:
        for write in (
            lambda: writer.create("a", draft),
            lambda: writer.update("a", 100000, draft),
            lambda: writer.own("a"),
            writer.admin_total,
        ):
            with pytest.raises(IndexUnavailable):
                write()
    finally:
        pool.close()
