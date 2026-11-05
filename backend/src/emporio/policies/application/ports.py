from collections.abc import Sequence
from typing import Protocol

from emporio.policies.domain.policy_chunk import PolicyChunk, PolicyHit


class PolicyIndex(Protocol):
    def search(self, question: str, k: int) -> Sequence[PolicyHit]: ...

    def replace_all(self, chunks: Sequence[PolicyChunk]) -> None: ...


class PolicySource(Protocol):
    def chunks(self) -> Sequence[PolicyChunk]: ...
