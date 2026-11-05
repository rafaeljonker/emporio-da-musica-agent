from emporio.catalog.application.ports import CatalogRepository
from emporio.catalog.domain.search import SearchResult, search_products
from emporio.shared.money import Money


class SearchProducts:
    def __init__(self, repo: CatalogRepository) -> None:
        self._repo = repo

    def __call__(
        self, query: str, max_price: Money | None = None, include_unavailable: bool = False
    ) -> SearchResult:
        return search_products(
            self._repo.products(),
            self._repo.categories(),
            query,
            max_price=max_price,
            include_unavailable=include_unavailable,
        )
