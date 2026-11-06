from emporio.support.domain.ai_tells import Tell, ai_tells
from emporio.support.domain.bubbles import pace_bubbles, split_bubbles, strip_channel_markup


def test_split_caps_at_three_bubbles_merging_the_shortest_neighbours() -> None:
    assert split_bubbles("a\n\n b \n\n\nccc\n\nd\n\ne") == ("a\nb", "ccc", "d\ne")


def test_capped_reply_keeps_every_word_and_no_longer_reads_as_too_many_bubbles() -> None:
    # promocoes, gemma-h100-fp8: four balloons, the question alone at the end
    text = (
        "Tem sim. No momento a gente tá com promoção de violões e ukuleles.\n\n"
        "Tem o Crafter HT-100 Folk por R$ 1.967,18, com 18% de desconto sobre os R$ 2.399.\n\n"
        "Nos ukuleles tem o Ohana CK-20 por R$ 439,20, com 20% de desconto.\n\n"
        "Algum desses faz seu estilo?"
    )
    bubbles = split_bubbles(text)
    assert len(bubbles) == 3
    assert bubbles[-1].endswith("Algum desses faz seu estilo?")
    assert " ".join(bubbles).replace(".", "").split() == text.replace(".", "").split()
    assert Tell.TOO_MANY_BUBBLES not in ai_tells("\n\n".join(bubbles))


def test_split_drops_empty_parts() -> None:
    assert split_bubbles("\n\n  \n\nolá\n\n") == ("olá",)


def test_first_bubble_has_no_delay() -> None:
    assert pace_bubbles(("a",)) == (0,)


def test_delay_is_clamped() -> None:
    assert pace_bubbles(("x", "a" * 5)) == (0, 700)
    assert pace_bubbles(("x", "a" * 200)) == (0, 2400)
    assert pace_bubbles(("x", "a" * 50)) == (0, 1500)


def test_total_pacing_capped_at_3000() -> None:
    assert pace_bubbles(("x", "a" * 200, "a" * 20)) == (0, 2400, 600)


def test_empty_thought_prefix_is_removed() -> None:
    assert split_bubbles("<|channel>thought\n<channel|>Oi, tudo bem?") == ("Oi, tudo bem?",)


def test_non_empty_thought_block_is_removed_entirely() -> None:
    text = "<|channel>thought\no cliente quer um violão\n\nvou buscar<channel|>Temos sim."
    assert split_bubbles(text) == ("Temos sim",)


def test_stray_channel_tokens_are_removed() -> None:
    assert strip_channel_markup("Oi<channel|> tudo<|channel>") == "Oi tudo"


def test_text_without_markup_is_untouched() -> None:
    assert strip_channel_markup("Fica R$ 2.199 <no pix>") == "Fica R$ 2.199 <no pix>"


def test_markup_only_reply_is_empty() -> None:
    assert split_bubbles("<|channel>thought\n<channel|>") == ()


def test_bubbles_drop_the_final_period_of_every_line() -> None:
    # A closing "." on each chat message reads as written by an AI, not typed on WhatsApp.
    text = "Tem sim.\n\nO Yamaha C40 sai por R$ 599,90.\nE no PIX fica R$ 569,91."
    assert split_bubbles(text) == (
        "Tem sim",
        "O Yamaha C40 sai por R$ 599,90\nE no PIX fica R$ 569,91",
    )


def test_bubbles_keep_question_marks_exclamations_and_ellipses() -> None:
    text = "Quer ver?\n\nOpa!\n\nDeixa eu ver..."
    assert split_bubbles(text) == ("Quer ver?", "Opa!", "Deixa eu ver...")


def test_bubbles_keep_inner_periods() -> None:
    assert split_bubbles("Custa R$ 2.399. Tem em estoque.") == ("Custa R$ 2.399. Tem em estoque",)
