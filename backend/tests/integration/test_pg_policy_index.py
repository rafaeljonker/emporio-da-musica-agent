from collections.abc import Sequence

import psycopg
import pytest
from psycopg import sql
from psycopg_pool import ConnectionPool

from emporio.policies.infrastructure.pdf_sections import read_policy_chunks
from emporio.policies.infrastructure.pg_policy_index import TSQUERY, PgPolicyIndex
from tests.fakes.hash_embedder import HashEmbedder

pytestmark = pytest.mark.postgres


def _index(pool: ConnectionPool, *, hybrid: bool = True) -> PgPolicyIndex:
    index = PgPolicyIndex(pool, HashEmbedder(), hybrid=hybrid)
    index.replace_all(read_policy_chunks())
    return index


def test_replace_all_is_idempotent(pg_pool: ConnectionPool, pg_conn: psycopg.Connection) -> None:
    _index(pg_pool)
    _index(pg_pool)

    row = pg_conn.execute("SELECT count(*) FROM policy_chunks").fetchone()
    assert row is not None
    assert row[0] == 25


def test_full_text_matches_without_accents(
    pg_pool: ConnectionPool, pg_conn: psycopg.Connection
) -> None:
    index = _index(pg_pool)

    refund = [h.chunk for h in index.search("devolucao", 5)]
    assert any("devolução" in c.body.lower() for c in refund)
    assert "2" in [h.chunk.section_id for h in index.search("domingo", 5)]


def test_vector_only_mode_returns_k_hits(pg_pool: ConnectionPool) -> None:
    hits = _index(pg_pool, hybrid=False).search("prazo de troca", 4)

    assert len(hits) == 4


def test_stopword_only_question_does_not_fail(pg_pool: ConnectionPool) -> None:
    hits = _index(pg_pool).search("o que é", 5)

    assert len(hits) <= 5


@pytest.mark.parametrize(
    ("question", "word"), [("devolucao", "devolução"), ("garantia dos violoes", "violões")]
)
def test_full_text_side_matches_without_accents(
    pg_pool: ConnectionPool, pg_conn: psycopg.Connection, question: str, word: str
) -> None:
    _index(pg_pool)

    rows = pg_conn.execute(
        sql.SQL("SELECT body FROM policy_chunks WHERE tsv @@ {}").format(sql.SQL(TSQUERY)),
        {"text": question},
    ).fetchall()

    assert any(word in r[0].lower() for r in rows)


class _WrongDimensionEmbedder(HashEmbedder):
    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


def test_failed_replace_all_keeps_previous_rows(
    pg_pool: ConnectionPool, pg_conn: psycopg.Connection
) -> None:
    _index(pg_pool)

    broken = PgPolicyIndex(pg_pool, _WrongDimensionEmbedder())
    with pytest.raises(psycopg.Error):
        broken.replace_all(read_policy_chunks())

    row = pg_conn.execute("SELECT count(*) FROM policy_chunks").fetchone()
    assert row is not None
    assert row[0] == 25
