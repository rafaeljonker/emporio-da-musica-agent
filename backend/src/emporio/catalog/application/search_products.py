from emporio.catalog.application.ports import CatalogFilter, CatalogRepository
from emporio.catalog.domain.search import SearchResult, named_categories, search_products
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
        pool = self._repo.search(query, flt, POOL)
        return search_products(pool, categories, query, include_unavailable=include_unavailable)
