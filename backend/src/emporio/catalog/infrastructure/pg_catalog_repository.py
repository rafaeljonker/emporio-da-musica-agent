from collections.abc import Collection, Iterator, Mapping, Sequence
from contextlib import contextmanager
from decimal import Decimal
from functools import cached_property
from typing import LiteralString

import psycopg
from pgvector import Vector
from psycopg_pool import ConnectionPool, PoolTimeout

from emporio.catalog.application.ports import CatalogFilter
from emporio.catalog.domain.pricing import Promotion
from emporio.catalog.domain.product import Category, Product, ProductStatus
from emporio.db import IndexUnavailable
from emporio.embeddings import TextEmbedder
from emporio.shared.money import Money

_COLUMNS = "p.id, p.name, p.category_id, p.description, p.specs, p.price, p.stock, p.status"

# The best active promotion's final price, unrounded like the research §8 predicate.
_FINAL_PRICE = (
    "p.price * (100 - coalesce((SELECT max(x.percent) FROM promotions x"
    " WHERE x.product_id = p.id AND x.active), 0)) / 100"
)

# Iterative scans keep a filtered HNSW search from returning too few rows (research §6).
_HNSW = "SET LOCAL hnsw.iterative_scan = relaxed_order; SET LOCAL hnsw.ef_search = 100"

# RRF (k = 60) of full text, trigram on name and glued code, and vector. Each branch inlines
# the filter: an `id IN (SELECT ...)` form measured ~60% slower. The tsquery is OR-ed and cast
# once, so lexemes are stemmed once (as in pg_policy_index). `%%` is psycopg's escaped `%`.
_SEARCH = """
WITH fts AS MATERIALIZED (
  SELECT p.id, row_number() OVER (ORDER BY ts_rank_cd(p.tsv, q.ts) DESC, p.id) AS r
  FROM products p,
       (SELECT replace(plainto_tsquery('portuguese', f_unaccent(%(text)s))::text, ' & ', ' | ')
               ::tsquery AS ts) q
  WHERE p.tsv @@ q.ts AND {flt}
  ORDER BY ts_rank_cd(p.tsv, q.ts) DESC, p.id LIMIT 40),
trgm AS MATERIALIZED (
  SELECT p.id, row_number() OVER (ORDER BY greatest(
           word_similarity(lower(f_unaccent(%(text)s)), p.name_key),
           word_similarity(regexp_replace(lower(f_unaccent(%(text)s)), '[^a-z0-9]', '', 'g'),
                           p.code_key)) DESC, p.id) AS r
  FROM products p
  WHERE (lower(f_unaccent(%(text)s)) <%% p.name_key
         OR regexp_replace(lower(f_unaccent(%(text)s)), '[^a-z0-9]', '', 'g') <%% p.code_key)
    AND {flt}
  ORDER BY r LIMIT 40),
vec AS MATERIALIZED (
  SELECT p.id, row_number() OVER (ORDER BY p.embedding <=> %(embedding)s, p.id) AS r
  FROM products p WHERE p.embedding IS NOT NULL AND {flt}
  ORDER BY p.embedding <=> %(embedding)s LIMIT 40),
fused AS (
  SELECT id, sum(1.0 / (60 + r)) AS score
  FROM (SELECT id, r FROM fts UNION ALL SELECT id, r FROM trgm UNION ALL SELECT id, r FROM vec) u
  GROUP BY id)
SELECT {columns}
FROM fused JOIN products p USING (id)
ORDER BY fused.score DESC, p.id
LIMIT %(k)s
"""

_GET_MANY = "SELECT {columns} FROM products p WHERE p.id = ANY(%s) ORDER BY p.id".replace(
    "{columns}", _COLUMNS
)
_PROMOTED = """
SELECT {columns} FROM products p
WHERE p.status = 'active' AND p.stock > 0
  AND EXISTS (SELECT 1 FROM promotions x WHERE x.product_id = p.id AND x.active)
ORDER BY p.id
""".replace("{columns}", _COLUMNS)


def _filter(flt: CatalogFilter) -> LiteralString:
    """Only the clauses this filter needs, so the planner sees no `param IS NULL` branches."""
    clauses: list[LiteralString] = ["true"]
    if flt.category_ids is not None:
        clauses.append("p.category_id = ANY(%(cats)s)")
    if flt.available_only:
        clauses.append("(p.status = 'active' AND p.stock > 0)")
    if flt.max_price is not None:
        clauses.append(f"{_FINAL_PRICE} <= %(max_price)s")
    return "(" + " AND ".join(clauses) + ")"


def _product(row: tuple[int, str, int, str, Mapping[str, object], Decimal, int, str]) -> Product:
    id_, name, category_id, description, specs, price, stock, status = row
    return Product(
        id=id_,
        name=name,
        category_id=category_id,
        description=description,
        price=Money(price),
        stock=stock,
        status=ProductStatus(status),
        specs=tuple(sorted((k, str(v)) for k, v in specs.items())),
    )


class PgCatalogRepository:
    def __init__(self, pool: ConnectionPool, embedder: TextEmbedder) -> None:
        self._pool = pool
        self._embedder = embedder

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection]:
        try:
            with self._pool.connection() as conn:
                yield conn
        except (psycopg.OperationalError, PoolTimeout) as err:
            raise IndexUnavailable from err

    def get(self, product_id: int) -> Product | None:
        found = self.get_many([product_id])
        return found[0] if found else None

    def get_many(self, ids: Collection[int]) -> Sequence[Product]:
        with self._connection() as conn:
            rows = conn.execute(
                _GET_MANY,
                (list(ids),),
            ).fetchall()
        return [_product(r) for r in rows]

    @cached_property
    def _categories(self) -> tuple[Category, ...]:
        # Category edits are out of scope, so one read per instance is enough.
        with self._connection() as conn:
            rows = conn.execute("SELECT id, name, description FROM categories ORDER BY id")
            return tuple(Category(*r) for r in rows.fetchall())

    def categories(self) -> Sequence[Category]:
        return self._categories

    def promotions_for(self, ids: Collection[int]) -> Sequence[Promotion]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT id, product_id, percent, label, active FROM promotions"
                " WHERE product_id = ANY(%s) ORDER BY id",
                (list(ids),),
            ).fetchall()
        return [Promotion(*r) for r in rows]

    def promoted(self) -> Sequence[Product]:
        with self._connection() as conn:
            rows = conn.execute(_PROMOTED).fetchall()
        return [_product(r) for r in rows]

    def search(self, query: str, flt: CatalogFilter, k: int) -> Sequence[Product]:
        if not query.strip():
            return []
        params = {
            "text": query,
            "embedding": Vector(self._embedder.embed_query(query)),
            "cats": sorted(flt.category_ids) if flt.category_ids is not None else None,
            "max_price": flt.max_price.amount if flt.max_price is not None else None,
            "k": k,
        }
        sql = _SEARCH.format(flt=_filter(flt), columns=_COLUMNS)
        with self._connection() as conn, conn.transaction():
            conn.execute(_HNSW)
            rows = conn.execute(sql, params).fetchall()
        return [_product(r) for r in rows]
