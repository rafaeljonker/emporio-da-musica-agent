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


ADVERSARIAL = [
    ("R$ 1.299", "R$ 11.299", False),
    ("R$ 2.199", "R$ 2.199,00.", True),
    ("R$ 2.199", "2199 reais", True),
    ("R$ 2.199", "R$ 2.199,90", False),
    ("R$ 2.089,05", "R$ 2.089,05", True),
    ("R$ 2.089", "R$ 2.089,05", False),
    ("R$ 2.199", "R$2199,00", True),
    ("@store_open", "Não estamos abertos agora, a gente tá fechado.", False),
    ("@store_open", "Agora tá fechado. Amanhã estamos abertos das 9h às 18h.", False),
    ("@store_open", "Tá aberto sim! Estamos abertos até as 18h.", True),
    ("@store_closed", "Estamos abertos até as 18h, depois fechamos.", False),
    ("@store_closed", "Tá aberto sim! Hoje não fechamos pro almoço.", False),
    ("@store_closed", "Agora tá fechado. Amanhã estamos abertos das 9h.", True),
    ("@has_it", "Esse modelo saiu de linha e não está disponível.", False),
    ("@has_it", "Saiu de linha, mas temos sim outros 7 cordas.", False),
    ("@has_it", "Não temos em estoque, saiu de linha.", False),
    ("@has_it", "Temos sim, tá disponível.", True),
    ("@return_no", "Não consigo ver seu pedido, mas pode devolver sim.", False),
    (
        "@return_no",
        "O prazo de arrependimento já passou, mas a garantia legal de 90 dias pode valer.",
        True,
    ),
    ("@return_no", "Já passou o prazo de 7 dias.", True),
    ("@return_no", "O prazo de 7 dias venceu em 25/01.", True),
    ("@return_no", "O prazo de 7 dias ainda não passou.", False),
    ("@return_yes", "Sim, entendo. Mas o prazo de 7 dias já passou.", False),
    ("@return_yes", "Você não está dentro do prazo.", False),
    ("@return_yes", "Pode devolver sim, está dentro do prazo.", True),
    ("@legal_warranty", "A garantia já acabou.", False),
    ("@legal_warranty", "Vale a garantia legal de 90 dias.", True),
    ("@status_delivered", "Não consigo passar detalhes da entrega sem confirmar o e-mail.", False),
    ("@status_delivered", "Seu pedido foi entregue em 18/01.", True),
    ("@claim_delivered", "Não consigo passar detalhes da entrega sem confirmar o e-mail.", False),
    ("@claim_delivered", "Ele já foi entregue.", True),
    ("@installments_9", "Dá em até 9x de R$ 100", True),
    ("@installments_9", "19x", False),
    ("@installments_9", "nove parcelas", True),
    ("@regret_7", "17 dias", False),
    ("@declines_accessory", "Aqui a gente trabalha só com instrumentos.", True),
    ("@declines_accessory", "Tem sim, qual cor?", False),
    ("@asks_model", "Qual modelo você procura?", True),
    ("@asks_model", "Custa um valor bom.", False),
]


@pytest.mark.parametrize(("token", "spoken", "expected"), ADVERSARIAL)
def test_group_judges_real_answers(token: str, spoken: str, expected: bool) -> None:
    assert matches(token, normalize(spoken)) is expected
