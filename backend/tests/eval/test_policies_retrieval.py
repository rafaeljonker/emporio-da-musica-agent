import tomllib
from pathlib import Path

import pytest
from psycopg_pool import ConnectionPool

from emporio.embeddings import E5Embedder
from emporio.policies.application.ingest_policies import IngestPolicies
from emporio.policies.infrastructure.pdf_sections import PdfPolicySource
from emporio.policies.infrastructure.pg_policy_index import PgPolicyIndex

pytestmark = [pytest.mark.eval, pytest.mark.postgres]

CASES = tomllib.loads(
    (Path(__file__).parents[2] / "evals" / "policies_retrieval.toml").read_text(encoding="utf-8")
)["case"]


def _hit_rates(index: PgPolicyIndex) -> dict[int, float]:
    ranks: list[int | None] = []
    for case in CASES:
        ids = [h.chunk.section_id for h in index.search(case["question"], 5)]
        ranks.append(ids.index(case["expected"]) + 1 if case["expected"] in ids else None)
        if ranks[-1] is None or ranks[-1] > 1:
            print(f"  miss@1 {case['question']!r} want {case['expected']} got {ids}")
    return {k: sum(r is not None and r <= k for r in ranks) / len(ranks) for k in (1, 3, 5)}


def test_hybrid_retrieval_hit_at_5(pg_pool: ConnectionPool) -> None:
    embedder = E5Embedder()
    index = PgPolicyIndex(pg_pool, embedder)
    IngestPolicies(PdfPolicySource(), index)()
    rows = {
        mode: _hit_rates(PgPolicyIndex(pg_pool, embedder, hybrid=mode == "hybrid"))
        for mode in ("vector", "hybrid")
    }
    print(f"\n| mode | hit@1 | hit@3 | hit@5 |  ({len(CASES)} questions)\n|---|---|---|---|")
    for mode, r in rows.items():
        print(f"| {mode} | {r[1]:.2f} | {r[3]:.2f} | {r[5]:.2f} |")
    assert rows["hybrid"][5] >= 0.9
