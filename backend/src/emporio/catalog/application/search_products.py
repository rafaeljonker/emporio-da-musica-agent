from emporio.catalog.application.ports import CatalogFilter, CatalogRepository
from emporio.catalog.domain.search import NoMatch, SearchResult, named_categories, search_products
from emporio.shared.money import Money

POOL = 40


class SearchProducts:
    def __init__(self, repo: CatalogRepository) -> None:
        self._repo = repo

    def __call__(
        self, query: str, max_price: Money | None = None, include_unavailable: bool = False
    ) -> SearchResult:
        categories = self._repo.categories()
        # Availability stays with the grader, so a hidden exact hit is reported with its status.
        flt = CatalogFilter(named_categories(categories, query) or None, False, max_price)
        found = self._grade(query, flt, include_unavailable)
        if isinstance(found, NoMatch) and flt.category_ids is not None:
            # The category is a soft filter: "7 cordas" names Cordas Orquestrais, yet the
            # 7-string guitar is a Violão.
            found = self._grade(query, CatalogFilter(None, False, max_price), include_unavailable)
        return found

    def _grade(self, query: str, flt: CatalogFilter, include_unavailable: bool) -> SearchResult:
        pool = self._repo.search(query, flt, POOL)
        return search_products(
            pool, self._repo.categories(), query, include_unavailable=include_unavailable
        )
