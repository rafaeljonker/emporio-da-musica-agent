from collections.abc import Sequence

import psycopg
from pgvector import Vector

from emporio.embeddings import TextEmbedder
from emporio.policies.domain.policy_chunk import PolicyChunk, PolicyHit

_VECTOR_ONLY = """
SELECT c.section_id, c.title, c.parent_title, c.body, 1 - (c.embedding <=> %(q)s) AS score
FROM policy_chunks c
ORDER BY c.embedding <=> %(q)s
LIMIT %(k)s
"""

# Reciprocal rank fusion (constant 60) of a vector ranking and an OR-ed full-text ranking.
# plainto_tsquery ANDs terms; swapping ' & ' for ' | ' makes any matching term count.
# A stopword-only question gives an empty tsquery, which matches nothing.
# Shared with the tests. Do not re-parse the text through to_tsquery: that stems twice.
TSQUERY = (
    "to_tsquery('portuguese',"
    " replace(plainto_tsquery('portuguese', f_unaccent(%(text)s))::text, ' & ', ' | '))"
)

_HYBRID = """
WITH vec AS (
    SELECT section_id, row_number() OVER (ORDER BY embedding <=> %(q)s) AS rank
    FROM policy_chunks
    ORDER BY embedding <=> %(q)s
    LIMIT 20
), fts AS (
    SELECT section_id,
           row_number() OVER (ORDER BY ts_rank(tsv, query.q) DESC) AS rank
    FROM policy_chunks,
         (SELECT {tsquery} AS q) AS query
    WHERE tsv @@ query.q
    ORDER BY ts_rank(tsv, query.q) DESC
    LIMIT 20
), fused AS (
    SELECT coalesce(vec.section_id, fts.section_id) AS section_id,
           coalesce(1.0 / (60 + vec.rank), 0) + coalesce(1.0 / (60 + fts.rank), 0) AS score
    FROM vec FULL OUTER JOIN fts ON vec.section_id = fts.section_id
)
SELECT c.section_id, c.title, c.parent_title, c.body, fused.score
FROM fused JOIN policy_chunks c ON c.section_id = fused.section_id
ORDER BY fused.score DESC, c.section_id
LIMIT %(k)s
""".replace("{tsquery}", TSQUERY)


class PgPolicyIndex:
    def __init__(
        self, conn: psycopg.Connection, embedder: TextEmbedder, *, hybrid: bool = True
    ) -> None:
        self._conn = conn
        self._embedder = embedder
        self._hybrid = hybrid

    def search(self, question: str, k: int) -> Sequence[PolicyHit]:
        params = {"q": Vector(self._embedder.embed_query(question)), "text": question, "k": k}
        sql = _HYBRID if self._hybrid else _VECTOR_ONLY
        rows = self._conn.execute(sql, params).fetchall()
        self._conn.commit()  # read-only; end the implicit transaction
        return [PolicyHit(PolicyChunk(r[0], r[1], r[2], r[3]), float(r[4])) for r in rows]

    def replace_all(self, chunks: Sequence[PolicyChunk]) -> None:
        vectors = self._embedder.embed_passages([c.embedding_text for c in chunks])
        with self._conn.transaction(), self._conn.cursor() as cur:
            cur.execute("DELETE FROM policy_chunks")
            cur.executemany(
                "INSERT INTO policy_chunks (section_id, title, parent_title, body, embedding)"
                " VALUES (%s, %s, %s, %s, %s)",
                [
                    (c.section_id, c.title, c.parent_title, c.body, Vector(v))
                    for c, v in zip(chunks, vectors, strict=True)
                ],
            )
