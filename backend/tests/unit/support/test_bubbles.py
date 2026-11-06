from emporio.support.domain.bubbles import pace_bubbles, split_bubbles


def test_split_caps_at_three_bubbles() -> None:
    assert split_bubbles("a\n\n b \n\n\nc\n\nd\n\ne") == ("a", "b", "c\n\nd\n\ne")


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
