from emporio.catalog.domain.product import ProductStatus
from emporio.catalog.domain.search import Candidates, Exact, NoMatch, SearchResult, search_products
from emporio.shared.money import Money
from tests.unit.catalog.factories import category, m, product

GUITARRAS, BATERIAS, VIOLAO, METAIS, CORDAS = 1, 3, 5, 7, 8

CATEGORIES = (
    category(id=GUITARRAS, name="Guitarras"),
    category(id=BATERIAS, name="Baterias e Percussão"),
    category(id=VIOLAO, name="Violões"),
    category(id=METAIS, name="Instrumentos de Sopro (Metais)"),
    category(id=CORDAS, name="Cordas Orquestrais"),
)

CATALOG = (
    product(id=95, name="Takamine GD20 Dreadnought Natural", category_id=VIOLAO, price="2199"),
    product(id=100, name="Takamine GC5CE Elétrico Nylon Natural", category_id=VIOLAO, price="3299"),
    product(id=105, name="Takamine GN51CE Elétrico Aço Natural", category_id=VIOLAO, price="4199"),
    product(id=115, name="Takamine GC1CE Elétrico Nylon Natural", category_id=VIOLAO, price="2499"),
    product(id=81, name="Yamaha C40 Nylon Natural", category_id=VIOLAO, price="599.90"),
    product(id=89, name="Shelby SN-100 Folk Aço Preto", category_id=VIOLAO, price="549"),
    product(
        id=113,
        name="Shelby SN-7C 7 Cordas Nylon Natural",
        category_id=VIOLAO,
        price="749",
        status=ProductStatus.DISCONTINUED,
    ),
    product(id=1, name="Fender Stratocaster Player", category_id=GUITARRAS, price="7999"),
)


def search(
    query: str, max_price: Money | None = None, *, include_unavailable: bool = False
) -> SearchResult:
    return search_products(CATALOG, CATEGORIES, query, max_price, include_unavailable)


def ids(result: SearchResult) -> tuple[int, ...]:
    assert isinstance(result, Candidates)
    return tuple(p.id for p in result.products)


def test_exact_model_query_returns_exact() -> None:
    result = search("Takamine GD20")
    assert isinstance(result, Exact)
    assert result.product.id == 95


def test_brand_only_query_returns_all_candidates_sorted_by_price() -> None:
    assert ids(search("takamine")) == (95, 115, 100, 105)


def test_category_plural_with_max_price() -> None:
    assert ids(search("violões", max_price=m("1000"))) == (89, 81)


def test_category_only_query_lists_the_whole_category() -> None:
    assert ids(search("violão")) == (89, 81, 95, 115, 100, 105)


def test_category_word_and_stopwords_narrow_the_query() -> None:
    assert ids(search("violões da takamine")) == (95, 115, 100, 105)


def test_unavailable_products_hidden_by_default() -> None:
    assert isinstance(search("Shelby SN-7C"), NoMatch)


def test_unavailable_included_when_asked() -> None:
    result = search("Shelby SN-7C", include_unavailable=True)
    assert isinstance(result, Exact)
    assert result.product.id == 113


def test_category_word_inside_a_product_name_still_finds_it() -> None:
    result = search("shelby 7 cordas", include_unavailable=True)
    assert isinstance(result, Exact)
    assert result.product.id == 113


def test_typo_falls_back_to_fuzzy() -> None:
    result = search("takamine gd 2O")
    assert isinstance(result, Exact)
    assert result.product.id == 95


def test_unknown_returns_no_match() -> None:
    assert isinstance(search("bateria eletronica roland"), NoMatch)
