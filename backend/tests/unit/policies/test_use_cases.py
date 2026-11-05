import pytest

from emporio.policies.application.ingest_policies import EmptyPolicySource, IngestPolicies
from emporio.policies.application.search_policies import SearchPolicies
from emporio.policies.domain.policy_chunk import PolicyChunk
from tests.unit.policies.fakes import FakePolicySource, InMemoryPolicyIndex


def _chunk(section_id: str, title: str, body: str) -> PolicyChunk:
    return PolicyChunk(section_id=section_id, title=title, parent_title=None, body=body)


CHUNKS = (
    _chunk("1", "Trocas", "troca em ate 30 dias"),
    _chunk("2", "Horario", "aberto de segunda a sabado"),
    _chunk("3", "Frete", "frete gratis acima de 500"),
)


def test_search_returns_top_k_hits() -> None:
    index = InMemoryPolicyIndex(list(CHUNKS))

    hits = SearchPolicies(index)("horario de segunda", k=1)

    assert [hit.chunk.section_id for hit in hits] == ["2"]


def test_blank_question_returns_empty_without_index_call() -> None:
    index = InMemoryPolicyIndex(list(CHUNKS))

    assert SearchPolicies(index)("   ") == ()
    assert index.search_calls == 0


def test_ingest_replaces_all_and_returns_count() -> None:
    index = InMemoryPolicyIndex([_chunk("9", "Velho", "antigo")])

    count = IngestPolicies(FakePolicySource(CHUNKS), index)()

    assert count == 3
    assert index.chunks == list(CHUNKS)


def test_ingest_refuses_empty_source() -> None:
    index = InMemoryPolicyIndex([_chunk("9", "Velho", "antigo")])

    with pytest.raises(EmptyPolicySource):
        IngestPolicies(FakePolicySource(), index)()
    assert len(index.chunks) == 1
