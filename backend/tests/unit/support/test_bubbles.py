from emporio.support.domain.ai_tells import Tell, ai_tells
from emporio.support.domain.bubbles import pace_bubbles, split_bubbles


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
    assert " ".join(bubbles).split() == text.split()
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
