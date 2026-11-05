from emporio.catalog.application.ports import CatalogRepository, ProductIndex
from emporio.catalog.domain.search import Candidates, NoMatch

_POOL = 10


class RecommendProducts:
    def __init__(self, repo: CatalogRepository, index: ProductIndex) -> None:
        self._repo = repo
        self._index = index

    def __call__(self, need: str, limit: int = 5) -> Candidates | NoMatch:
        if not need.strip():
            return NoMatch()
        by_id = {p.id: p for p in self._repo.products()}
        # Availability is filtered here, after retrieval, never in the index query.
        ranked = (by_id.get(i) for i in self._index.similar(need, _POOL))
        found = tuple(p for p in ranked if p is not None and p.is_available)[:limit]
        return Candidates(found) if found else NoMatch()
