from decimal import Decimal

import psycopg
import pytest
from psycopg import sql
from psycopg_pool import ConnectionPool

from emporio.catalog.application.ports import CatalogFilter
from emporio.catalog.application.search_products import SearchProducts
from emporio.catalog.domain.pricing import best_active_promotion, quote_price
from emporio.catalog.domain.search import Candidates, Exact, NoMatch, SearchResult
from emporio.catalog.infrastructure.csv_catalog_repository import CsvCatalogRepository
from emporio.catalog.infrastructure.pg_catalog_repository import PgCatalogRepository
from emporio.catalog.infrastructure.pg_catalog_writer import PgCatalogWriter
from emporio.shared.money import Money
from tests.fakes.hash_embedder import HashEmbedder

pytestmark = pytest.mark.postgres

CSV = CsvCatalogRepository()


def _seed(pool: ConnectionPool) -> int:
    writer = PgCatalogWriter(pool, HashEmbedder())
    return writer.seed(CSV.categories(), CSV.products(), CSV.promotions())


def _count(conn: psycopg.Connection, table: str) -> int:
    row = conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()
    assert row is not None
    return row[0]


def _ids(result: SearchResult) -> set[int]:
    match result:
        case Exact(product):
            return {product.id}
        case Candidates(products):
            return {p.id for p in products}
        case NoMatch():
            return set()


def test_seed_is_idempotent_and_embeds_once(
    pg_pool: ConnectionPool, pg_conn: psycopg.Connection
) -> None:
    assert _seed(pg_pool) == 65
    assert _seed(pg_pool) == 0

    assert _count(pg_conn, "products") == 65
    assert _count(pg_conn, "categories") == 9
    assert _count(pg_conn, "promotions") == len(CSV.promotions())


def test_seed_removes_admin_rows(
    catalog_repo: PgCatalogRepository, pg_pool: ConnectionPool, pg_conn: psycopg.Connection
) -> None:
    pg_conn.execute(
        "INSERT INTO products (id, name, category_id, description, price, stock, status,"
        " source, owner, search_doc)"
        " VALUES (100000, 'Admin row', 5, '', 10, 1, 'active', 'admin', 'x', 'Admin row')"
    )
    pg_conn.commit()

    _seed(pg_pool)

    assert catalog_repo.get(100000) is None


def test_get_many_and_get(catalog_repo: PgCatalogRepository) -> None:
    found = catalog_repo.get(95)
    assert found is not None
    assert "GD20" in found.name
    assert catalog_repo.get(999999) is None
    assert {p.id for p in catalog_repo.get_many([95, 81, 999999])} == {95, 81}


def test_get_returns_the_csv_product(catalog_repo: PgCatalogRepository) -> None:
    expected = next(p for p in CSV.products() if p.id == 95)
    assert catalog_repo.get(95) == expected


@pytest.mark.parametrize(
    ("query", "product_id"),
    [("takamine gd 20", 95), ("SN-7C", 113), ("telecastr", 134), ("yamah c70", 82)],
)
def test_search_finds_codes_and_typos(
    catalog_repo: PgCatalogRepository, query: str, product_id: int
) -> None:
    top = [p.id for p in catalog_repo.search(query, CatalogFilter(), 10)][:3]
    assert product_id in top


def test_available_only_excludes_unavailable(catalog_repo: PgCatalogRepository) -> None:
    found = {p.id for p in catalog_repo.search("violão", CatalogFilter(available_only=True), 40)}
    assert found
    assert not found & {113, 130, 136, 96}


def test_max_price_uses_promotional_final_price(catalog_repo: PgCatalogRepository) -> None:
    p, best = next(
        (p, best)
        for p in CSV.products()
        if (best := best_active_promotion(CSV.promotions_for([p.id]))) is not None
    )
    final = quote_price(p, best).final.amount

    at = catalog_repo.search(p.name, CatalogFilter(max_price=Money(final)), 10)
    below = catalog_repo.search(p.name, CatalogFilter(max_price=Money(final - Decimal("0.01"))), 10)

    assert p.id in {x.id for x in at}
    assert p.id not in {x.id for x in below}


def test_category_filter_returns_whole_category(catalog_repo: PgCatalogRepository) -> None:
    violoes = {p.id for p in CSV.products() if p.category_id == 5}
    found = catalog_repo.search("violões", CatalogFilter(category_ids=frozenset({5})), 40)
    assert len(violoes) == 35
    assert {p.id for p in found} == violoes


def test_row_without_embedding_is_found_by_text(
    catalog_repo: PgCatalogRepository, pg_conn: psycopg.Connection
) -> None:
    pg_conn.execute("UPDATE products SET embedding = NULL WHERE id = 95")
    pg_conn.commit()

    assert 95 in {p.id for p in catalog_repo.search("takamine gd20", CatalogFilter(), 5)}


def test_blank_query_returns_nothing(catalog_repo: PgCatalogRepository) -> None:
    assert catalog_repo.search("  ", CatalogFilter(), 5) == []


def test_promoted_matches_csv(catalog_repo: PgCatalogRepository) -> None:
    expected = {
        p.id
        for p in CSV.products()
        if p.is_available and best_active_promotion(CSV.promotions_for([p.id])) is not None
    }
    assert {p.id for p in catalog_repo.promoted()} == expected


def test_promotions_for_returns_csv_rows(catalog_repo: PgCatalogRepository) -> None:
    ids = {x.product_id for x in CSV.promotions()}
    assert set(catalog_repo.promotions_for(ids)) == set(CSV.promotions())


def test_seven_strings_finds_shelby_outside_its_named_category(
    catalog_repo: PgCatalogRepository,
) -> None:
    found = SearchProducts(catalog_repo)("7 cordas", include_unavailable=True)
    assert 113 in _ids(found)


def test_violoes_under_ceiling_matches_csv(catalog_repo: PgCatalogRepository) -> None:
    ceiling = Money(Decimal(1000))
    expected = SearchProducts(CSV)("violões até 1000", ceiling)
    found = SearchProducts(catalog_repo)("violões até 1000", ceiling)
    assert isinstance(found, Candidates)
    assert _ids(found) == _ids(expected)
