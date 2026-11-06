import pytest

from emporio.support.domain.ai_tells import Tell, ai_tells

EN = chr(0x2013)
EM = chr(0x2014)
CLEAN = (
    "Yamaha FG800, folk com tampo sólido de spruce, som bem encorpado pro preço.\n\n"
    "Sai R$ 1.299, ou R$ 1.234,05 no PIX. Tenho 7 em estoque.\n\n"
    "É pra tocar sozinha ou acompanhando voz?"
)

CASES = [
    (Tell.EM_DASH, f"Sai R$ 1.299 {EM} no PIX."),
    (Tell.EM_DASH, f"Isso {EN} ou aquilo."),
    (Tell.MARKDOWN, "Sai **R$ 1.299** no PIX."),
    (Tell.MARKDOWN, "Opções:\n- violão\n- guitarra"),
    (Tell.MARKDOWN, "Opções:\n1. violão\n2. guitarra"),
    (Tell.MARKDOWN, "# Preço"),
    (Tell.BANNED_PHRASE, "OTIMA pergunta, vou ver."),
    (Tell.BANNED_PHRASE, "Sinta-se a vontade pra olhar."),
    (Tell.TEXTSPEAK, "Vc quer o preto?"),
    (Tell.EMOJI, "Boa escolha \U0001f3b8"),
    (Tell.EXCLAMATIONS, "Show! Chegou! Perfeito."),
    (Tell.MULTIPLE_QUESTIONS, "Qual cor? Qual tamanho?"),
    (Tell.QUESTION_NOT_LAST, "Qual cor?\n\nTenho 7 em estoque."),
    (Tell.TOO_MANY_BUBBLES, "a\n\nb\n\nc\n\nd"),
    (Tell.LONG_BUBBLE, "x" * 281),
]


@pytest.mark.parametrize(("tell", "text"), CASES)
def test_tells_detects_each_rule(tell: Tell, text: str) -> None:
    assert tell in ai_tells(text)


def test_every_tell_is_covered() -> None:
    assert {t for t, _ in CASES} == set(Tell)


def test_clean_reply_has_no_tells() -> None:
    assert ai_tells(CLEAN) == ()


@pytest.mark.parametrize(
    "text",
    [f"Amanhã é das 9h{EN}18h.", "Temos pós-venda em 12x de R$ 183,25.", "Uma só exclamação!"],
)
def test_legit_text_is_not_a_tell(text: str) -> None:
    assert ai_tells(text) == ()


@pytest.mark.parametrize(
    "text",
    [
        "Veja https://x.com/p?id=3 agora.\n\nQual cor?",
        "#12345 saiu hoje.",
        "Código abc__def confirmado.",
    ],
)
def test_edge_cases_are_not_tells(text: str) -> None:
    assert ai_tells(text) == ()


@pytest.mark.parametrize(
    "text",
    [
        "Prezado cliente, tudo bem?",
        "Prezada Letícia, segue o preço.",
        "Prezados, bom dia.",
        "Qualquer dúvida, estou à disposição.",
        "Fico à disposição pra mais coisa.",
        "Não hesite em chamar.",
        "Nao hesite, viu.",
        "Fico feliz em ajudar!",
        "Fico feliz em te ajudar.",
        "Espero ter ajudado.",
        "Ótima pergunta, vou ver.",
        "Estou aqui para ajudar.",
        "Estou aqui para te ajudar no que precisar.",
        "Sinta-se à vontade.",
        "Sinta se a vontade!",
        "Como posso te ajudar hoje?",
        "Como posso ajudar hoje?",
        "Fico feliz,  em   ajudar.",
    ],
)
def test_banned_phrase_variants_are_caught(text: str) -> None:
    assert Tell.BANNED_PHRASE in ai_tells(text)


def test_mano_is_textspeak() -> None:
    assert Tell.TEXTSPEAK in ai_tells("E aí mano, quer o preto?")
    assert ai_tells("O Manoel passou aqui.") == ()


@pytest.mark.parametrize("text", ["Esse é *muito* bom.", "Sai *R$ 1.299* no PIX."])
def test_single_asterisk_italics_is_markdown(text: str) -> None:
    assert Tell.MARKDOWN in ai_tells(text)


@pytest.mark.parametrize(
    "text", ["Violão - preto, folk.", "Preto - 12 cordas.", "Sai 1299 - no PIX."]
)
def test_spaced_hyphen_used_as_a_dash_is_a_tell(text: str) -> None:
    assert Tell.EM_DASH in ai_tells(text)


@pytest.mark.parametrize(
    "text",
    ["Abrimos das 9h-18h.", "Abrimos das 9h - 18h.", "Pós-venda e sub-total.", "Vale 2 * 3 = 6."],
)
def test_hyphens_and_asterisks_in_legit_use_are_not_tells(text: str) -> None:
    assert ai_tells(text) == ()
