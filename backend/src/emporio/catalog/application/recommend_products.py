from emporio.catalog.application.ports import CatalogFilter, CatalogRepository
from emporio.catalog.domain.search import Candidates, NoMatch


class RecommendProducts:
    def __init__(self, repo: CatalogRepository) -> None:
        self._repo = repo

    def __call__(self, need: str, limit: int = 5) -> Candidates | NoMatch:
        if limit <= 0 or not need.strip():
            return NoMatch()
        found = tuple(self._repo.search(need, CatalogFilter(available_only=True), limit))[:limit]
        return Candidates(found) if found else NoMatch()
