import hashlib
from collections.abc import Sequence

import psycopg
from pgvector import Vector
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool, PoolTimeout

from emporio.catalog.domain.pricing import Promotion
from emporio.catalog.domain.product import Category, Product, search_document
from emporio.db import IndexUnavailable
from emporio.embeddings import TextEmbedder

# A row whose search document is unchanged keeps its embedding (both new values are NULL).
_UPSERT_PRODUCT = """
INSERT INTO products (id, name, category_id, description, specs, price, stock, status, source,
                      search_doc, embedding, embedded_hash)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'seed', %s, %s, %s)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name, category_id = EXCLUDED.category_id,
  description = EXCLUDED.description, specs = EXCLUDED.specs, price = EXCLUDED.price,
  stock = EXCLUDED.stock, status = EXCLUDED.status, source = 'seed', owner = NULL,
  search_doc = EXCLUDED.search_doc,
  embedding = coalesce(EXCLUDED.embedding, products.embedding),
  embedded_hash = coalesce(EXCLUDED.embedded_hash, products.embedded_hash),
  updated_at = now()
"""


def _hash(doc: str) -> str:
    return hashlib.sha256(doc.encode()).hexdigest()


class PgCatalogWriter:
    def __init__(self, pool: ConnectionPool, embedder: TextEmbedder) -> None:
        self._pool = pool
        self._embedder = embedder

    def seed(
        self,
        categories: Sequence[Category],
        products: Sequence[Product],
        promotions: Sequence[Promotion],
    ) -> int:
        """Reset the catalog to the seed; returns how many products it embedded."""
        names = {c.id: c.name for c in categories}
        docs = {
            p.id: search_document(p.name, names.get(p.category_id, ""), p.description, p.specs)
            for p in products
        }
        try:
            with self._pool.connection() as conn:
                stored = dict(conn.execute("SELECT id, embedded_hash FROM products").fetchall())
            stale = [p.id for p in products if stored.get(p.id) != _hash(docs[p.id])]
            vectors = dict(
                zip(stale, self._embedder.embed_passages([docs[i] for i in stale]), strict=True)
            )
            with self._pool.connection() as conn, conn.transaction(), conn.cursor() as cur:
                cur.execute("DELETE FROM promotions")
                cur.execute("DELETE FROM products WHERE source = 'admin'")
                cur.executemany(
                    "INSERT INTO categories (id, name, description) VALUES (%s, %s, %s)"
                    " ON CONFLICT (id) DO UPDATE SET"
                    " name = EXCLUDED.name, description = EXCLUDED.description",
                    [(c.id, c.name, c.description) for c in categories],
                )
                cur.executemany(
                    _UPSERT_PRODUCT,
                    [
                        (
                            p.id,
                            p.name,
                            p.category_id,
                            p.description,
                            Jsonb(dict(p.specs)),
                            p.price.amount,
                            p.stock,
                            p.status.value,
                            docs[p.id],
                            Vector(vectors[p.id]) if p.id in vectors else None,
                            _hash(docs[p.id]) if p.id in vectors else None,
                        )
                        for p in products
                    ],
                )
                cur.executemany(
                    "INSERT INTO promotions (id, product_id, percent, label, active)"
                    " VALUES (%s, %s, %s, %s, %s)",
                    [(x.id, x.product_id, x.percent, x.label, x.active) for x in promotions],
                )
        except (psycopg.OperationalError, PoolTimeout) as err:
            raise IndexUnavailable from err
        return len(vectors)
