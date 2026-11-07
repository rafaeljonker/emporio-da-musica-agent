import tomllib
from pathlib import Path

import pytest
from psycopg_pool import ConnectionPool

from emporio.catalog.application.ports import CatalogFilter
from emporio.catalog.infrastructure.csv_catalog_repository import CsvCatalogRepository
from emporio.catalog.infrastructure.pg_catalog_repository import PgCatalogRepository
from emporio.catalog.infrastructure.pg_catalog_writer import PgCatalogWriter
from emporio.platform.embeddings import E5Embedder

pytestmark = [pytest.mark.eval, pytest.mark.postgres]

CASES = tomllib.loads(
    (Path(__file__).parents[2] / "evals" / "products_retrieval.toml").read_text(encoding="utf-8")
)["case"]


def test_hybrid_product_retrieval_hit_at_5(pg_pool: ConnectionPool) -> None:
    embedder = E5Embedder()
    csv = CsvCatalogRepository()
    PgCatalogWriter(pg_pool, embedder).seed(csv.categories(), csv.products(), csv.promotions())
    catalog = PgCatalogRepository(pg_pool, embedder)
    ranks: dict[str, list[int | None]] = {}
    for case in CASES:
        ids = [p.id for p in catalog.search(case["query"], CatalogFilter(), 5)]
        rank = next((i + 1 for i, pid in enumerate(ids) if pid in case["expected"]), None)
        ranks.setdefault(case["group"], []).append(rank)
        if rank != 1:
            print(f"  miss@1 {case['query']!r} want {case['expected']} got {ids}")
    every = [r for group in ranks.values() for r in group]
    ranks["overall"] = every

    def hit(rs: list[int | None], k: int) -> float:
        return sum(r is not None and r <= k for r in rs) / len(rs)

    print(f"\n| group | n | hit@1 | hit@5 |  ({len(CASES)} queries)\n|---|---|---|---|")
    for group, rs in ranks.items():
        print(f"| {group} | {len(rs)} | {hit(rs, 1):.2f} | {hit(rs, 5):.2f} |")
    assert hit(every, 5) >= 0.9
