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
