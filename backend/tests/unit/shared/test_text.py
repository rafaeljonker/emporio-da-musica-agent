from emporio.shared.text import fold, stem, tokens


def test_fold_removes_accents_and_case() -> None:
    assert fold("  Violão  ELÉTRICO ") == "violao eletrico"


def test_tokens_stem_plurals() -> None:
    assert tokens("Violões e guitarras") == ("violao", "e", "guitarra")


def test_stem_keeps_short_words() -> None:
    assert stem("gs") == "gs"


def test_tokens_split_model_codes() -> None:
    assert tokens("Takamine GD-20") == ("takamine", "gd", "20")


def test_stem_matches_singular_and_plural_catalog_words() -> None:
    pairs = [
        ("digitais", "digital"),
        ("metais", "metal"),
        ("profissionais", "profissional"),
        ("niveis", "nivel"),
        ("captadores", "captador"),
        ("oboes", "oboe"),
    ]
    for plural, singular in pairs:
        assert stem(plural) == stem(singular) == singular


def test_stem_does_not_apply_al_rule_to_short_words() -> None:
    assert (stem("mais"), stem("pais")) == ("mai", "pai")
