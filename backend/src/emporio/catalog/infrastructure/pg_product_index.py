from collections.abc import Mapping, Sequence

import psycopg
from pgvector import Vector

from emporio.catalog.domain.product import Product
from emporio.embeddings import TextEmbedder


class PgProductIndex:
    def __init__(self, conn: psycopg.Connection, embedder: TextEmbedder) -> None:
        self._conn = conn
        self._embedder = embedder

    def similar(self, need: str, k: int) -> Sequence[int]:
        q = Vector(self._embedder.embed_query(need))
        with self._conn.transaction():
            rows = self._conn.execute(
                "SELECT product_id FROM product_embeddings"
                " ORDER BY embedding <=> %s, product_id LIMIT %s",
                (q, k),
            ).fetchall()
        return [r[0] for r in rows]

    def replace_all(self, products: Sequence[Product], category_names: Mapping[int, str]) -> None:
        texts = [
            f"{p.name}. {category_names.get(p.category_id, '')}. {p.description}" for p in products
        ]
        vectors = self._embedder.embed_passages(texts)
        with self._conn.transaction(), self._conn.cursor() as cur:
            cur.execute("DELETE FROM product_embeddings")
            cur.executemany(
                "INSERT INTO product_embeddings (product_id, embedding) VALUES (%s, %s)",
                [(p.id, Vector(v)) for p, v in zip(products, vectors, strict=True)],
            )
