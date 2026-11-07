import hashlib
import logging
from collections.abc import Sequence

import psycopg
from pgvector import Vector
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool, PoolTimeout

from emporio.catalog.domain.pricing import Promotion
from emporio.catalog.domain.product import Category, Product, ProductDraft, search_document
from emporio.catalog.infrastructure.pg_catalog_repository import (
    COLUMNS,
    catalog_connection,
    product_from_row,
)
from emporio.db import IndexUnavailable
from emporio.embeddings import TextEmbedder

logger = logging.getLogger(__name__)

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


_OWN = (
    "SELECT {columns} FROM products p WHERE p.source = 'admin' AND p.owner = %s ORDER BY p.id DESC"
).replace("{columns}", COLUMNS)


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

    def create(self, owner: str, draft: ProductDraft) -> Product:
        doc = self._document(draft)
        vector, digest = self._embed(doc)
        with catalog_connection(self._pool) as conn, conn.transaction():
            [(new_id,)] = conn.execute(
                "INSERT INTO products (id, name, category_id, description, specs, price, stock,"
                " status, source, owner, search_doc, embedding, embedded_hash)"
                " VALUES (nextval('products_admin_id_seq'), %s, %s, %s, %s, %s, %s, %s,"
                " 'admin', %s, %s, %s, %s) RETURNING id",
                (*_values(draft), owner, doc, vector, digest),
            ).fetchall()
            created = draft.with_id(new_id)
            _audit(conn, owner, "create", created)
        return created

    def update(self, owner: str, product_id: int, draft: ProductDraft) -> Product | None:
        with catalog_connection(self._pool) as conn:
            found = conn.execute(
                "SELECT embedded_hash FROM products WHERE id = %s AND source = 'admin'"
                " AND owner = %s",
                (product_id, owner),
            ).fetchone()
        if found is None:
            return None
        doc = self._document(draft)
        changed = found[0] != _hash(doc)
        vector, digest = self._embed(doc) if changed else (None, None)
        with catalog_connection(self._pool) as conn, conn.transaction():
            row = conn.execute(
                "UPDATE products SET name = %s, category_id = %s, description = %s, specs = %s,"
                " price = %s, stock = %s, status = %s, search_doc = %s,"
                " embedding = CASE WHEN %s THEN %s ELSE embedding END,"
                " embedded_hash = CASE WHEN %s THEN %s ELSE embedded_hash END,"
                " updated_at = now()"
                " WHERE id = %s AND source = 'admin' AND owner = %s RETURNING id",
                (*_values(draft), doc, changed, vector, changed, digest, product_id, owner),
            ).fetchone()
            if row is None:
                return None
            updated = draft.with_id(product_id)
            _audit(conn, owner, "update", updated)
        return updated

    def own(self, owner: str) -> Sequence[Product]:
        with catalog_connection(self._pool) as conn:
            rows = conn.execute(
                _OWN,
                (owner,),
            ).fetchall()
        return [product_from_row(r) for r in rows]

    def admin_total(self) -> int:
        with catalog_connection(self._pool) as conn:
            row = conn.execute("SELECT count(*) FROM products WHERE source = 'admin'").fetchone()
        return row[0] if row else 0

    def _document(self, draft: ProductDraft) -> str:
        with catalog_connection(self._pool) as conn:
            row = conn.execute(
                "SELECT name FROM categories WHERE id = %s", (draft.category_id,)
            ).fetchone()
        category = row[0] if row else ""
        return search_document(draft.name, category, draft.description, draft.specs)

    def _embed(self, doc: str) -> tuple[Vector | None, str | None]:
        """The vector and its document hash, or (None, None) when the embedder fails."""
        try:
            [vector] = self._embedder.embed_passages([doc])
        except Exception as err:  # any model failure: save the row, text search still finds it
            # The type only at warning: a traceback could carry the product text.
            logger.warning("product embed failed: %s", type(err).__name__)
            logger.debug("product embed traceback", exc_info=True)
            return None, None
        return Vector(vector), _hash(doc)


def _values(draft: ProductDraft) -> tuple[object, ...]:
    return (
        draft.name,
        draft.category_id,
        draft.description,
        Jsonb(dict(draft.specs)),
        draft.price.amount,
        draft.stock,
        draft.status.value,
    )


def _audit(conn: psycopg.Connection, actor: str, action: str, product: Product) -> None:
    after = {
        "id": product.id,
        "name": product.name,
        "category_id": product.category_id,
        "description": product.description,
        "specs": dict(product.specs),
        "price": str(product.price.amount),
        "stock": product.stock,
        "status": product.status.value,
    }
    conn.execute(
        "INSERT INTO catalog_audit (actor, action, product_id, after) VALUES (%s, %s, %s, %s)",
        (actor, action, product.id, Jsonb(after)),
    )
