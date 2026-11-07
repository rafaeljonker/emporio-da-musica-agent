import math
from concurrent.futures import ThreadPoolExecutor

import pytest

from emporio.platform.embeddings import EMBEDDING_DIM, E5Embedder
from emporio.policies.infrastructure.pdf_sections import read_policy_chunks

pytestmark = pytest.mark.eval


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_e5_real_vectors_are_384_unit_and_rank_related_text_higher() -> None:
    chunks = {c.section_id: c for c in read_policy_chunks()}
    passages = [chunks["4.1"].embedding_text, chunks["2"].embedding_text]
    embedder = E5Embedder()

    query = embedder.embed_query("posso devolver?")
    returns, other = embedder.embed_passages(passages)

    assert len(query) == len(returns) == EMBEDDING_DIM
    assert math.isclose(math.sqrt(_dot(query, query)), 1.0, abs_tol=1e-4)
    print(f"sim(query, 4.1)={_dot(query, returns):.4f} sim(query, 2)={_dot(query, other):.4f}")
    assert _dot(query, returns) > _dot(query, other)


def test_embed_query_from_threads_matches_sequential_run() -> None:
    embedder = E5Embedder()
    questions = [f"posso devolver o item {i}?" for i in range(8)]
    sequential = [embedder.embed_query(q) for q in questions]

    with ThreadPoolExecutor(max_workers=8) as pool:
        threaded = list(pool.map(embedder.embed_query, questions))

    assert threaded == sequential
