from emporio.policies.application.ports import PolicyIndex
from emporio.policies.domain.policy_chunk import PolicyHit


class SearchPolicies:
    def __init__(self, index: PolicyIndex) -> None:
        self._index = index

    def __call__(self, question: str, k: int = 5) -> tuple[PolicyHit, ...]:
        if not question.strip():
            return ()
        return tuple(self._index.search(question, k))
