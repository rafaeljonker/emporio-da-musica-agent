import pytest
from evals.verify import (
    Expect,
    UnknownGroup,
    expand,
    matches,
    normalize,
    verify,
)


@pytest.mark.parametrize(
    ("raw", "folded"),
    [
        ("R$ 2.199,00", "2199"),
        ("Fica R$2.199 no total", "fica 2199 no total"),
        ("R$ 1.967,18", "1967,18"),
        ("R$ 1.234.567", "1234567"),
        ("Violão ÁGIL", "violao agil"),
    ],
)
def test_normalize_strips_currency_dots_and_zero_cents(raw: str, folded: str) -> None:
    assert normalize(raw) == folded


def test_price_matches_every_spelling_of_the_same_amount() -> None:
    expected = "R$ 2.199"
    for spoken in ("R$ 2.199", "R$ 2.199,00", "2199 reais", "custa 2.199."):
        assert matches(expected, normalize(spoken))


def test_price_does_not_match_a_longer_number() -> None:
    assert not matches("R$ 199", normalize("R$ 2.199"))
    assert not matches("R$ 2.199", normalize("R$ 2.199,50"))


@pytest.mark.parametrize("spoken", ["9x de R$ 100", "em 9 parcelas", "nove vezes sem juros"])
def test_installment_group_accepts_each_paraphrase(spoken: str) -> None:
    assert matches("@installments_9", normalize(spoken))


def test_installment_group_rejects_another_count() -> None:
    assert not matches("@installments_9", normalize("em 12x de R$ 75"))
    assert not matches("@installments_9", normalize("19 parcelas"))


@pytest.mark.parametrize(
    "spoken",
    [
        "Esse modelo foi descontinuado",
        "Ele saiu de linha",
        "Não está mais disponível",
        "Esse não faz mais parte do catálogo",
    ],
)
def test_discontinued_group_accepts_each_paraphrase(spoken: str) -> None:
    assert matches("@discontinued", normalize(spoken))


def test_unknown_group_is_an_error() -> None:
    with pytest.raises(UnknownGroup):
        matches("@nope", "x")


def test_expand_fills_placeholders_and_lists() -> None:
    facts = {"n": "9", "names": ("Yamaha F310", "Fender CD-60")}
    assert expand("@installments_{n}", facts) == ("@installments_9",)
    assert expand("{names}", facts) == ("Yamaha F310", "Fender CD-60")


def test_all_of_needs_every_token() -> None:
    expect = Expect(all_of=("2199", "pix"))
    assert verify(expect, ("Sai R$ 2.199 no pix",), ()).passed
    assert not verify(expect, ("Sai R$ 2.199",), ()).passed


def test_any_of_needs_one_token() -> None:
    expect = Expect(any_of=("yamaha f310", "fender cd-60"))
    assert verify(expect, ("Temos a Fender CD-60",), ()).passed
    assert not verify(expect, ("Temos a Takamine",), ()).passed


def test_empty_any_of_candidates_fail_instead_of_passing_silently() -> None:
    assert not verify(Expect(any_of=()), ("oi",), ()).passed


def test_none_of_rejects_a_forbidden_token() -> None:
    expect = Expect(none_of=("@discontinued",))
    assert verify(expect, ("Tem sim",), ()).passed
    assert not verify(expect, ("Saiu de linha",), ()).passed


def test_ask_requires_the_last_bubble_to_end_with_a_question() -> None:
    expect = Expect(ask=True)
    assert verify(expect, ("Oi", "Qual modelo?"), ()).passed
    assert not verify(expect, ("Qual modelo?", "Me diz."), ()).passed


def test_expected_tools_must_all_be_used() -> None:
    expect = Expect(expect_tools=("search_products", "store_now"))
    verdict = verify(expect, ("ok",), ("search_products",))
    assert not verdict.passed
    assert "store_now" in verdict.failures[0]
    assert verify(expect, ("ok",), ("store_now", "search_products", "x")).passed
