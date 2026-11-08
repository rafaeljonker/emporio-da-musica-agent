import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from emporio.policies.domain.policy_chunk import PolicyChunk, PolicyHit


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


@dataclass(slots=True)
class InMemoryPolicyIndex:
    chunks: list[PolicyChunk] = field(default_factory=list)
    search_calls: int = 0

    def search(self, question: str, k: int) -> Sequence[PolicyHit]:
        self.search_calls += 1
        asked = _words(question)
        hits = [
            PolicyHit(chunk, float(len(asked & _words(chunk.embedding_text))))
            for chunk in self.chunks
        ]
        ranked = sorted(hits, key=lambda hit: hit.score, reverse=True)
        return [hit for hit in ranked if hit.score > 0][:k]

    def replace_all(self, chunks: Sequence[PolicyChunk]) -> None:
        self.chunks = list(chunks)


@dataclass(frozen=True, slots=True)
class FakePolicySource:
    _chunks: tuple[PolicyChunk, ...] = ()

    def chunks(self) -> Sequence[PolicyChunk]:
        return self._chunks
