from emporio.shared.text import fold, stem, tokens


def test_fold_removes_accents_and_case() -> None:
    assert fold("  Violão  ELÉTRICO ") == "violao eletrico"


def test_tokens_stem_plurals() -> None:
    assert tokens("Violões e guitarras") == ("violao", "e", "guitarra")


def test_stem_keeps_short_words() -> None:
    assert stem("gs") == "gs"


def test_tokens_split_model_codes() -> None:
    assert tokens("Takamine GD-20") == ("takamine", "gd", "20")
