import psycopg
import pytest

from emporio.policies.infrastructure.pdf_sections import read_policy_chunks
from emporio.policies.infrastructure.pg_policy_index import PgPolicyIndex
from tests.fakes.hash_embedder import HashEmbedder

pytestmark = pytest.mark.postgres


def _index(conn: psycopg.Connection, *, hybrid: bool = True) -> PgPolicyIndex:
    index = PgPolicyIndex(conn, HashEmbedder(), hybrid=hybrid)
    index.replace_all(read_policy_chunks())
    return index


def test_replace_all_is_idempotent(pg_conn: psycopg.Connection) -> None:
    _index(pg_conn)
    _index(pg_conn)

    row = pg_conn.execute("SELECT count(*) FROM policy_chunks").fetchone()
    assert row is not None
    assert row[0] == 25


def test_full_text_matches_without_accents(pg_conn: psycopg.Connection) -> None:
    index = _index(pg_conn)

    refund = [h.chunk for h in index.search("devolucao", 5)]
    assert any("devolução" in c.body.lower() for c in refund)
    assert "2" in [h.chunk.section_id for h in index.search("domingo", 5)]


def test_vector_only_mode_returns_k_hits(pg_conn: psycopg.Connection) -> None:
    hits = _index(pg_conn, hybrid=False).search("prazo de troca", 4)

    assert len(hits) == 4


def test_stopword_only_question_does_not_fail(pg_conn: psycopg.Connection) -> None:
    hits = _index(pg_conn).search("o que é", 5)

    assert len(hits) <= 5
