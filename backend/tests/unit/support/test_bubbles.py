from emporio.support.domain.bubbles import split_bubbles


def test_split_caps_at_three_bubbles() -> None:
    assert split_bubbles("a\n\n b \n\n\nc\n\nd\n\ne") == ("a", "b", "c\n\nd\n\ne")


def test_split_drops_empty_parts() -> None:
    assert split_bubbles("\n\n  \n\nolá\n\n") == ("olá",)
