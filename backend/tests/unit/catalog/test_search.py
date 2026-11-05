from emporio.catalog.domain.product import ProductStatus
from emporio.catalog.domain.search import Candidates, Exact, NoMatch, SearchResult, search_products
from emporio.shared.money import Money
from tests.unit.catalog.factories import category, m, product

GUITARRAS, BAIXOS, BATERIAS, TECLADOS, VIOLAO, METAIS, CORDAS, UKULELES = 1, 2, 3, 4, 5, 7, 8, 9

CATEGORIES = (
    category(id=GUITARRAS, name="Guitarras"),
    category(id=BAIXOS, name="Baixos"),
    category(id=BATERIAS, name="Baterias e Percussão"),
    category(
        id=TECLADOS,
        name="Teclados e Pianos",
        description="Pianos digitais, sintetizadores, arranjadores e controladores MIDI",
    ),
    category(id=VIOLAO, name="Violões"),
    category(id=METAIS, name="Instrumentos de Sopro (Metais)"),
    category(id=CORDAS, name="Cordas Orquestrais"),
    category(id=UKULELES, name="Ukuleles"),
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
    product(id=90, name="Crafter HT-100 Folk Aço Natural", category_id=VIOLAO, price="2399"),
    product(
        id=111, name="Rozini RV-175 7 Cordas Elétrico Natural", category_id=VIOLAO, price="1699"
    ),
    product(id=112, name="Tagima TW-7 7 Cordas Aço Natural", category_id=VIOLAO, price="999"),
    product(id=93, name="Martin D-28 Dreadnought Natural", category_id=VIOLAO, price="11499"),
    product(id=108, name="Martin D-28E Elétrico Aço Natural", category_id=VIOLAO, price="12000"),
    product(
        id=136,
        name="Ibanez Bass 2X Electric Bass",
        category_id=BAIXOS,
        price="441",
        status=ProductStatus.DISCONTINUED,
        description="Contrabaixo Precision de 4 cordas com captação split-coil.",
    ),
    product(
        id=144,
        name="Teclado Sintetizador Roland Synth 3 Pro",
        category_id=TECLADOS,
        price="9351",
        description="Teclado arranjador Yamaha com 61 teclas sensitivas.",
    ),
    product(
        id=145, name="Fender Stratocaster American Pro II", category_id=GUITARRAS, price="12500"
    ),
    product(
        id=135,
        name="Music Man Bass 1X Electric Bass",
        category_id=BAIXOS,
        price="8732",
        description="Contrabaixo elétrico Fender Jazz Bass com corpo em Alder.",
    ),
    product(
        id=137,
        name="Yamaha Bass 3X Electric Bass",
        category_id=BAIXOS,
        price="11445",
        description="Contrabaixo ativo de 5 cordas Ibanez com equalizador de 3 bandas.",
    ),
    product(
        id=142,
        name="Teclado Sintetizador Korg Synth 1 Pro",
        category_id=TECLADOS,
        price="1127",
        description="Sintetizador workstation Roland com 88 teclas pesadas.",
    ),
    product(
        id=143,
        name="Teclado Sintetizador Nord Synth 2 Pro",
        category_id=TECLADOS,
        price="19567",
        description="Piano de palco Nord Stage com seções independentes de piano, órgão e synth.",
    ),
    product(
        id=140, name="Bateria Acústica Pearl Kit 2 Studio", category_id=BATERIAS, price="13285"
    ),
    product(id=124, name="Kala KA-T Tenor Mogno", category_id=UKULELES, price="449.90"),
    product(id=125, name="Ohana TK-35G Tenor Sólido Natural", category_id=UKULELES, price="1299"),
    product(id=128, name="Kala KA-B Barítono Mogno", category_id=UKULELES, price="599"),
)


ALL_VIOLOES = (89, 81, 112, 111, 95, 90, 115, 100, 105, 93, 108)


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
    assert ids(search("violões", max_price=m("1000"))) == (89, 81, 112)


def test_category_only_query_lists_the_whole_category() -> None:
    assert ids(search("violão")) == ALL_VIOLOES


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


def test_typo_with_split_model_code_is_still_exact() -> None:
    result = search("gd 20")
    assert isinstance(result, Exact)
    assert result.product.id == 95


def test_prefix_of_a_name_word_matches() -> None:
    result = search("strato")
    assert isinstance(result, Exact)
    assert result.product.id == 145


def test_weak_fuzzy_similarity_is_no_match() -> None:
    assert isinstance(search("violino"), NoMatch)


def test_accessory_not_sold_is_no_match() -> None:
    assert isinstance(search("encordoamento"), NoMatch)


def test_bass_query_never_returns_a_violao() -> None:
    result = search("baixo 5 cordas")
    found = (result.product,) if isinstance(result, Exact) else ()
    found += result.products if isinstance(result, Candidates) else ()
    assert all(p.category_id == BAIXOS for p in found)


def test_wrong_model_number_is_never_exact() -> None:
    assert not isinstance(search("gd30"), Exact)


def test_wrong_model_number_with_brand_is_never_exact() -> None:
    assert not isinstance(search("takamine gd30"), Exact)


def test_price_words_do_not_fuzz_into_model_numbers() -> None:
    assert ids(search("violões até 1000")) == ALL_VIOLOES


def test_category_fallback_does_not_fuzz_the_whole_store() -> None:
    assert isinstance(search("bateria eletronica roland"), NoMatch)


def test_shopping_words_are_ignored() -> None:
    assert ids(search("violão mais barato")) == ALL_VIOLOES


def test_word_from_the_category_description_lists_the_category() -> None:
    assert ids(search("teclado digital")) == (142, 144, 143)


def test_piano_digital_lists_the_keyboards() -> None:
    assert ids(search("piano digital")) == (142, 144, 143)


def test_two_categories_list_both() -> None:
    assert set(ids(search("violões e guitarras"))) == {*ALL_VIOLOES, 145}


def test_word_only_in_one_description_is_exact() -> None:
    result = search("jazz bass")
    assert isinstance(result, Exact)
    assert result.product.id == 135


def test_empty_category_word_still_narrows_by_name() -> None:
    assert ids(search("violão 7 cordas")) == (112, 111)


def test_model_code_matches_hyphenated_name() -> None:
    result = search("martin d28")
    assert isinstance(result, Exact)
    assert result.product.id == 93


def test_glued_model_code_matches() -> None:
    result = search("sn100")
    assert isinstance(result, Exact)
    assert result.product.id == 89


def test_description_only_match_is_not_exact() -> None:
    assert not isinstance(search("teclado yamaha"), Exact)


def test_brand_only_in_a_description_is_not_exact() -> None:
    assert not isinstance(search("baixo ibanez"), Exact)


def test_bare_number_is_no_match() -> None:
    assert isinstance(search("1000"), NoMatch)


def test_unknown_number_is_never_fuzzed() -> None:
    result = search("sn 1000")
    assert not isinstance(result, Exact)
    assert not (isinstance(result, Candidates) and 90 in ids(result))
