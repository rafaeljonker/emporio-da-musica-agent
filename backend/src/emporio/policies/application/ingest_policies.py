from emporio.policies.application.ports import PolicyIndex, PolicySource
from emporio.shared.errors import DomainError


class EmptyPolicySource(DomainError):
    def __init__(self) -> None:
        super().__init__("The policy source yielded no chunks; refusing to wipe the index.")


class IngestPolicies:
    def __init__(self, source: PolicySource, index: PolicyIndex) -> None:
        self._source = source
        self._index = index

    def __call__(self) -> int:
        chunks = self._source.chunks()
        if not chunks:
            raise EmptyPolicySource
        self._index.replace_all(chunks)
        return len(chunks)
